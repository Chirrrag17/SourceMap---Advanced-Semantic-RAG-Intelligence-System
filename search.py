"""Small dependency-free BM25-style search with code-aware boosts."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .indexer import tokenize


@dataclass
class SearchResult:
    score: float
    path: str
    start_line: int
    end_line: int
    symbols: list[str]
    text: str


def search(index: dict, query: str, limit: int = 5, k1: float = 1.5, b: float = 0.75) -> list[SearchResult]:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    chunks = index.get("chunks", [])
    query_terms = tokenize(query)
    if not chunks or not query_terms:
        return []
    doc_terms = [chunk.get("tokens") or tokenize(chunk.get("text", "")) for chunk in chunks]
    lengths = [len(tokens) for tokens in doc_terms]
    avg_len = sum(lengths) / max(len(lengths), 1)
    doc_freq = Counter(term for term in set(query_terms) for tokens in doc_terms if term in set(tokens))
    query_counts = Counter(query_terms)
    query_lower = query.lower()
    results: list[SearchResult] = []
    n_docs = len(chunks)
    for chunk, tokens, length in zip(chunks, doc_terms, lengths):
        counts = Counter(tokens)
        score = 0.0
        for term, qtf in query_counts.items():
            df = doc_freq[term]
            if not df:
                continue
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            tf = counts[term]
            denom = tf + k1 * (1 - b + b * length / max(avg_len, 1))
            score += qtf * idf * (tf * (k1 + 1) / denom)
        path = chunk.get("path", "")
        symbols = chunk.get("symbols", [])
        searchable_path = re.sub(r"[/._-]+", " ", path.lower())
        searchable_symbols = " ".join(symbol.lower() for symbol in symbols)
        for term in set(query_terms):
            if term in searchable_path:
                score += 0.65
            if term in searchable_symbols:
                score += 1.25
        if query_lower.strip() and query_lower.strip() in chunk.get("text", "").lower():
            score += 0.5
        if score > 0:
            results.append(SearchResult(score, path, int(chunk.get("start_line", 1)), int(chunk.get("end_line", 1)), symbols, chunk.get("text", "")))
    results.sort(key=lambda result: (-result.score, result.path, result.start_line))
    return results[:limit]
