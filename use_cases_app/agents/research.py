"""
2) Research Agent — search → analyze → summarize.

Pattern: gather sources, extract insights, write a short brief.
Demo knowledge base (no web API key required).
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

# Tiny offline "search index" for demos
KB = {
    "langgraph": [
        "LangGraph builds agents as graphs of nodes and edges.",
        "State is shared memory that travels through the graph.",
        "Cycles let agents retry until a goal is met.",
    ],
    "agents": [
        "An AI agent plans, uses tools, and can loop on failure.",
        "Multi-agent systems assign specialists to subtasks.",
        "Memory and routing are key for reliable agents.",
    ],
    "python": [
        "Python is popular for AI because of rich libraries.",
        "TypedDict and Pydantic help structure agent state.",
        "LangChain and LangGraph are common Python agent stacks.",
    ],
}


class ResearchState(TypedDict):
    query: str
    sources: list[str]
    analysis: list[str]
    summary: str
    status: str


def search(state: ResearchState) -> dict:
    q = (state.get("query") or "").lower()
    hits: list[str] = []
    for key, facts in KB.items():
        if key in q or any(w in q for w in key.split()):
            hits.extend(facts)
    if not hits:
        # fallback: mix a few general facts
        hits = KB["agents"][:2] + KB["langgraph"][:1]
    return {"sources": hits[:5], "status": "searched"}


def analyze(state: ResearchState) -> dict:
    sources = state.get("sources") or []
    analysis = [f"Insight: {s}" for s in sources]
    # Highlight graph keywords
    if any("graph" in s.lower() or "state" in s.lower() for s in sources):
        analysis.append("Insight: Prefer explicit state + edges for production agents.")
    return {"analysis": analysis, "status": "analyzed"}


def summarize(state: ResearchState) -> dict:
    q = state.get("query") or ""
    bullets = state.get("analysis") or []
    body = "\n".join(f"• {b.replace('Insight: ', '')}" for b in bullets[:4])
    summary = (
        f"Research brief for: “{q}”\n\n"
        f"{body}\n\n"
        f"Sources used: {len(state.get('sources') or [])} · Status: done"
    )
    return {"summary": summary, "status": "done"}


def build_research_agent():
    g = StateGraph(ResearchState)
    g.add_node("search", search)
    g.add_node("analyze", analyze)
    g.add_node("summarize", summarize)

    g.add_edge(START, "search")
    g.add_edge("search", "analyze")
    g.add_edge("analyze", "summarize")
    g.add_edge("summarize", END)
    return g.compile()


def run_research(query: str) -> ResearchState:
    app = build_research_agent()
    return app.invoke(
        {
            "query": query,
            "sources": [],
            "analysis": [],
            "summary": "",
            "status": "started",
        }
    )
