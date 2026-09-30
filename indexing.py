"""Local repository clone, chunking, and optional embedding pipeline."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from codebase_context.indexer import DEFAULT_EXTENSIONS, iter_source_files, tokenize

from .models import CodeChunk

LANGUAGES = {".py": "python", ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".ts": "typescript", ".tsx": "typescript", ".java": "java", ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php", ".cs": "csharp", ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".kt": "kotlin", ".swift": "swift", ".scala": "scala", ".sql": "sql", ".sh": "shell", ".md": "markdown"}
DECL = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:def|class|function|interface|type|enum|struct|trait|module)\s+([\w$]+)")


def clone_repository(clone_url: str, destination: str | Path, token: str | None = None) -> Path:
    dest = Path(destination).expanduser().resolve()
    safe_url = clone_url
    if token and clone_url.startswith("https://github.com/"):
        safe_url = clone_url.replace("https://", f"https://x-access-token:{token}@", 1)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        subprocess.run(["git", "-C", str(dest), "fetch", "--depth", "1", "origin"], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", str(dest), "reset", "--hard", "FETCH_HEAD"], check=True, capture_output=True, text=True)
    else:
        subprocess.run(["git", "clone", "--depth", "1", safe_url, str(dest)], check=True, capture_output=True, text=True)
    return dest


def revision(root: Path) -> str:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def parse_tree_sitter(source: bytes, language: str):
    """Optional tree-sitter hook. Returns None when parser packages are absent."""
    try:
        from tree_sitter_language_pack import get_parser
        parser = get_parser(language)
        return parser.parse(source)
    except (ImportError, LookupError, ValueError):
        return None


def chunk_repository(root: Path, repo_id: str, lines_per_chunk: int = 70, overlap: int = 10) -> list[CodeChunk]:
    root = root.resolve()
    step = lines_per_chunk - overlap
    if step < 1:
        raise ValueError("overlap must be smaller than lines_per_chunk")
    chunks: list[CodeChunk] = []
    rev = revision(root) if (root / ".git").exists() else "local"
    for path in iter_source_files(root, extensions=DEFAULT_EXTENSIONS):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        language = LANGUAGES.get(path.suffix.lower(), "text")
        for start in range(0, len(lines), step):
            end = min(start + lines_per_chunk, len(lines))
            content = "\n".join(lines[start:end]).strip()
            if content:
                names = [m.group(1) for line in lines[start:end] if (m := DECL.match(line))]
                name = names[0] if names else Path(rel).stem
                chunk_id = hashlib.sha1(f"{repo_id}:{rev}:{rel}:{start}:{content}".encode()).hexdigest()
                chunks.append(CodeChunk(chunk_id, repo_id, rel, language, "symbol" if names else "block", name, start + 1, end, content, None, rev))
            if end == len(lines):
                break
    return chunks


def embed_chunks(chunks: list[CodeChunk], api_key: str, model: str = "text-embedding-3-small", batch_size: int = 96):
    if not api_key:
        return chunks
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the 'openai' optional dependency to generate embeddings") from exc
    client = OpenAI(api_key=api_key)
    for offset in range(0, len(chunks), batch_size):
        batch = chunks[offset:offset + batch_size]
        response = client.embeddings.create(model=model, input=[f"{c.file_path} {c.chunk_name}\n{c.content}" for c in batch])
        for chunk, item in zip(batch, response.data):
            chunk.embedding = item.embedding
    return chunks


def persist_chunks(chunks: list[CodeChunk], root: Path, repo_id: str):
    folder = root / ".sourcemap"
    folder.mkdir(exist_ok=True)
    target = folder / f"{hashlib.sha1(repo_id.encode()).hexdigest()[:16]}.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps([c.to_dict() for c in chunks]), encoding="utf-8")
    tmp.replace(target)
    return target


def load_chunks(path: str | Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
