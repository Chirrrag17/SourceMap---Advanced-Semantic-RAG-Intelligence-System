"""Repository discovery, line chunking, and JSON index persistence."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

INDEX_VERSION = 1
DEFAULT_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".java", ".kt", ".go", ".rs", ".c", ".h", ".cc", ".cpp", ".hpp",
    ".cs", ".rb", ".php", ".swift", ".scala", ".sql", ".sh", ".bash",
    ".yaml", ".yml", ".toml", ".json", ".md", ".rst", ".txt",
}
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "vendor",
    "dist", "build", "target", "coverage", "__pycache__", ".next", ".idea",
}
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\w\s]", re.UNICODE)
SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:def|class|function|interface|type|enum|struct|trait|module)\s+([A-Za-z_$][\w$]*)"
    r"|^\s*(?:public|private|protected|static|final|abstract|const|let|var)\s+(?:[\w<>\[\],.?]+\s+)+([A-Za-z_$][\w$]*)\s*(?:\(|=|;)"
)


@dataclass
class Chunk:
    chunk_id: str
    path: str
    start_line: int
    end_line: int
    text: str
    tokens: list[str]
    symbols: list[str]


def tokenize(text: str) -> list[str]:
    """Split identifiers into normalized terms, preserving useful code words."""
    terms: list[str] = []
    for token in TOKEN_RE.findall(text.lower()):
        if token.isalnum() or "_" in token:
            terms.append(token.replace("_", " "))
            terms.extend(part for part in re.split(r"[_\W]+", token) if len(part) > 1)
    return [part for term in terms for part in term.split() if part]


def _is_candidate(path: Path, root: Path, extensions: set[str], max_bytes: int) -> bool:
    try:
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS or part.startswith(".") and part not in {".github"} for part in rel.parts[:-1]):
            return False
        if path.suffix.lower() not in extensions:
            return False
        return path.stat().st_size <= max_bytes
    except (OSError, ValueError):
        return False


def iter_source_files(root: Path, extensions: set[str] | None = None, max_bytes: int = 1_000_000) -> Iterator[Path]:
    extensions = extensions or DEFAULT_EXTENSIONS
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (d.startswith(".") and d != ".github"))
        current_path = Path(current)
        for name in sorted(files):
            candidate = current_path / name
            if _is_candidate(candidate, root, extensions, max_bytes):
                yield candidate


def chunk_file(root: Path, path: Path, lines_per_chunk: int = 80, overlap: int = 12) -> list[Chunk]:
    if lines_per_chunk <= 0 or overlap < 0 or overlap >= lines_per_chunk:
        raise ValueError("Require lines_per_chunk > overlap >= 0")
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = content.splitlines()
    if not lines:
        return []
    rel = path.relative_to(root).as_posix()
    result: list[Chunk] = []
    step = lines_per_chunk - overlap
    for start in range(0, len(lines), step):
        end = min(start + lines_per_chunk, len(lines))
        body = "\n".join(lines[start:end]).strip()
        if body:
            digest = hashlib.sha1(f"{rel}:{start + 1}:{body}".encode("utf-8")).hexdigest()[:12]
            symbols = []
            for line in lines[start:end]:
                match = SYMBOL_RE.match(line)
                if match:
                    symbol = next((group for group in match.groups() if group), None)
                    if symbol:
                        symbols.append(symbol)
            result.append(Chunk(digest, rel, start + 1, end, body, tokenize(body), symbols))
        if end == len(lines):
            break
    return result


def build_index(root: str | Path, lines_per_chunk: int = 80, overlap: int = 12, max_bytes: int = 1_000_000) -> dict:
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Repository directory not found: {root}")
    chunks: list[Chunk] = []
    file_count = 0
    for path in iter_source_files(root, max_bytes=max_bytes):
        file_chunks = chunk_file(root, path, lines_per_chunk, overlap)
        if file_chunks:
            file_count += 1
            chunks.extend(file_chunks)
    return {
        "version": INDEX_VERSION,
        "root": str(root),
        "file_count": file_count,
        "chunk_count": len(chunks),
        "chunks": [asdict(chunk) for chunk in chunks],
    }


def save_index(index: dict, path: str | Path) -> Path:
    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    temp.replace(output)
    return output


def load_index(path: str | Path) -> dict:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if data.get("version") != INDEX_VERSION or not isinstance(data.get("chunks"), list):
        raise ValueError("Unsupported or malformed index file")
    return data
