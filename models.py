"""Small typed records shared by the indexing and retrieval layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class CodeChunk:
    chunk_id: str
    repo_id: str
    file_path: str
    language: str
    chunk_type: str
    chunk_name: str
    line_start: int
    line_end: int
    content: str
    embedding: list[float] | None = None
    revision: str = "local"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Source:
    file_path: str
    line_start: int
    line_end: int
    relevance_score: float
    code_snippet: str
    chunk_name: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
