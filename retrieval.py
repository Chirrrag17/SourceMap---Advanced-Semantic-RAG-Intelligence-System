"""Hybrid retrieval with optional vector and LLM providers; lexical works offline."""

from __future__ import annotations

import math
from collections import Counter

from codebase_context.indexer import tokenize


def lexical_retrieve(chunks: list[dict], query: str, top_k: int = 5) -> list[dict]:
    terms = tokenize(query)
    if not terms:
        return []
    docs = [tokenize(" ".join([c.get("file_path", ""), c.get("chunk_name", ""), c.get("content", "")])) for c in chunks]
    df = Counter(term for term in set(terms) for doc in docs if term in set(doc))
    avg_len = sum(map(len, docs)) / max(1, len(docs))
    ranked = []
    for chunk, doc in zip(chunks, docs):
        counts = Counter(doc); score = 0.0
        for term in terms:
            tf = counts[term]
            if tf:
                idf = math.log(1 + (len(docs) - df[term] + .5) / (df[term] + .5))
                score += idf * tf * 2.5 / (tf + 1.5 * (.25 + .75 * len(doc) / max(avg_len, 1)))
        if score:
            ranked.append((score, chunk))
    ranked.sort(key=lambda item: (-item[0], item[1].get("file_path", ""), item[1].get("line_start", 0)))
    return [{**chunk, "score": score} for score, chunk in ranked[:top_k]]


def pinecone_retrieve(query_vector: list[float], api_key: str, index_name: str, namespace: str, top_k: int = 5):
    try:
        from pinecone import Pinecone
    except ImportError as exc:
        raise RuntimeError("Install the 'pinecone' optional dependency to query Pinecone") from exc
    index = Pinecone(api_key=api_key).Index(index_name)
    result = index.query(vector=query_vector, top_k=top_k, namespace=namespace, include_metadata=True)
    return [{"score": m.score, **(m.metadata or {})} for m in result.matches]


def rerank(query: str, chunks: list[dict]) -> list[dict]:
    """Small deterministic reranker; replace with a cross-encoder when available."""
    q = set(tokenize(query))
    for chunk in chunks:
        content = set(tokenize(f"{chunk.get('chunk_name','')} {chunk.get('file_path','')} {chunk.get('content','')}"))
        overlap = len(q & content) / max(1, len(q))
        chunk["rerank_score"] = float(chunk.get("score", 0)) + overlap * 0.25
    return sorted(chunks, key=lambda c: (-c["rerank_score"], c.get("file_path", "")))
