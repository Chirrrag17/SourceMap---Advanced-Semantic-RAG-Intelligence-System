"""Optional LangGraph query workflow with a dependency-free retrieval fallback."""

from __future__ import annotations

from .retrieval import lexical_retrieve, rerank


def answer_query(query: str, chunks: list[dict], top_k: int = 5) -> dict:
    try:
        from langgraph.graph import END, START, StateGraph
        from typing_extensions import TypedDict
    except ImportError:
        results = rerank(query, lexical_retrieve(chunks, query, top_k))
        return _format(query, results, "LangGraph is not installed; returned local lexical retrieval results.")

    class State(TypedDict, total=False):
        query: str
        chunks: list[dict]
        results: list[dict]

    def retrieve(state: State):
        return {"results": rerank(state["query"], lexical_retrieve(state["chunks"], state["query"], top_k))}

    graph = StateGraph(State)
    graph.add_node("retrieve", retrieve)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", END)
    result = graph.compile().invoke({"query": query, "chunks": chunks})
    return _format(query, result.get("results", []), "Retrieved sources are shown below.")


def _format(query: str, results: list[dict], note: str) -> dict:
    sources = [{"file_path": c.get("file_path"), "lines": f"{c.get('line_start')}-{c.get('line_end')}", "relevance_score": round(float(c.get("rerank_score", c.get("score", 0))), 4), "code_snippet": c.get("content", "")[:1200], "chunk_name": c.get("chunk_name", "")} for c in results]
    if not sources:
        return {"query": query, "answer": "No matching code was found. Try a symbol name, file path, or narrower question.", "sources": [], "related_files": [], "confidence": 0.0, "note": note}
    answer = "Relevant code was found in " + ", ".join(f"{s['file_path']} (lines {s['lines']})" for s in sources[:3]) + ". Review the cited snippets to verify the behavior."
    return {"query": query, "answer": answer, "sources": sources, "related_files": list(dict.fromkeys(s["file_path"] for s in sources[1:])), "confidence": min(0.95, round(sources[0]["relevance_score"] / (sources[0]["relevance_score"] + 1), 2)), "note": note}
