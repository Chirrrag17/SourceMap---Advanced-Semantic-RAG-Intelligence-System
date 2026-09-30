"""Command-line interface for local indexing and search."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .indexer import build_index, load_index, save_index
from .search import search


def _default_index(root: Path) -> Path:
    return root / ".context-engine" / "index.json"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codebase-context", description="Index and search a local code repository.")
    sub = parser.add_subparsers(dest="command", required=True)
    index_cmd = sub.add_parser("index", help="Build a local search index")
    index_cmd.add_argument("repository", type=Path)
    index_cmd.add_argument("--index-path", type=Path)
    index_cmd.add_argument("--chunk-lines", type=int, default=80)
    search_cmd = sub.add_parser("search", help="Search a previously built index")
    search_cmd.add_argument("query", help="Natural language or code terms to search")
    search_cmd.add_argument("--index-path", type=Path)
    search_cmd.add_argument("--top", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "index":
            root = args.repository.expanduser().resolve()
            index = build_index(root, lines_per_chunk=args.chunk_lines)
            output = save_index(index, args.index_path or _default_index(root))
            print(f"Indexed {index['file_count']} files into {index['chunk_count']} chunks")
            print(f"Index: {output.resolve()}")
            return 0
        if args.top < 1:
            parser.error("--top must be at least 1")
        path = args.index_path.expanduser() if args.index_path else None
        if path is None:
            parser.error("search needs --index-path (for example, .context-engine/index.json)")
        index = load_index(path)
        hits = search(index, args.query, limit=args.top)
        if not hits:
            print("No matching code chunks found.")
            return 0
        for rank, hit in enumerate(hits, 1):
            symbols = f" | symbols: {', '.join(hit.symbols)}" if hit.symbols else ""
            print(f"[{rank}] {hit.path}:{hit.start_line}-{hit.end_line}  score={hit.score:.3f}{symbols}")
            snippet = hit.text.strip().replace("\n", "\n    ")
            print(f"    {snippet[:900]}{'…' if len(snippet) > 900 else ''}\n")
        return 0
    except (OSError, ValueError, NotADirectoryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
