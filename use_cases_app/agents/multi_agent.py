"""
4) Multi-Agent — specialists solving together.

Pattern: supervisor routes to Writer / Analyst / Critic, then merges.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class TeamState(TypedDict):
    question: str
    route: str
    writer_out: str
    analyst_out: str
    critic_out: str
    final: str
    log: list[str]


def supervisor(state: TeamState) -> dict:
    q = (state.get("question") or "").lower()
    log = list(state.get("log") or [])
    if any(w in q for w in ("data", "number", "metric", "analyze", "stats")):
        route = "analyst"
    elif any(w in q for w in ("review", "critic", "risk", "wrong")):
        route = "critic"
    else:
        route = "writer"
    log.append(f"Supervisor → {route}")
    return {"route": route, "log": log}


def writer(state: TeamState) -> dict:
    q = state.get("question") or ""
    out = (
        f"[Writer] Draft answer:\n"
        f"LangGraph helps build reliable agents for: {q}. "
        f"Use clear state, nodes, and edges."
    )
    log = list(state.get("log") or [])
    log.append("Writer finished draft")
    return {"writer_out": out, "log": log}


def analyst(state: TeamState) -> dict:
    q = state.get("question") or ""
    out = (
        f"[Analyst] Findings for “{q}”:\n"
        f"- Pattern fit: high for graph workflows\n"
        f"- Risk: low if retries + validation exist\n"
        f"- Score: 8.5 / 10 (demo)"
    )
    log = list(state.get("log") or [])
    log.append("Analyst finished report")
    return {"analyst_out": out, "log": log}


def critic(state: TeamState) -> dict:
    draft = state.get("writer_out") or state.get("analyst_out") or state.get("question") or ""
    out = (
        f"[Critic] Review:\n"
        f"- Clarity: good\n"
        f"- Missing: production observability\n"
        f"- Suggestion: add checkpoints before shipping\n"
        f"(based on: {draft[:80]}…)"
    )
    log = list(state.get("log") or [])
    log.append("Critic finished review")
    return {"critic_out": out, "log": log}


def merge(state: TeamState) -> dict:
    parts = [p for p in (state.get("writer_out"), state.get("analyst_out"), state.get("critic_out")) if p]
    # Always run a light critic pass after specialist for "team" feel when writer/analyst only
    if state.get("route") in ("writer", "analyst") and not state.get("critic_out"):
        extra = (
            "\n\n[Critic · quick pass] Looks solid for a demo. "
            "Next: add tests and tracing."
        )
    else:
        extra = ""
    final = "\n\n".join(parts) + extra
    log = list(state.get("log") or [])
    log.append("Merge complete")
    return {"final": final.strip(), "log": log}


def route_to_specialist(state: TeamState) -> Literal["writer", "analyst", "critic"]:
    return state.get("route") or "writer"  # type: ignore[return-value]


def after_specialist(state: TeamState) -> Literal["critic", "merge"]:
    # Writer/analyst → critic for collaboration; critic alone → merge
    if state.get("route") == "critic":
        return "merge"
    if state.get("critic_out"):
        return "merge"
    return "critic"


def build_multi_agent():
    g = StateGraph(TeamState)
    g.add_node("supervisor", supervisor)
    g.add_node("writer", writer)
    g.add_node("analyst", analyst)
    g.add_node("critic", critic)
    g.add_node("merge", merge)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route_to_specialist,
        {"writer": "writer", "analyst": "analyst", "critic": "critic"},
    )
    g.add_conditional_edges(
        "writer",
        after_specialist,
        {"critic": "critic", "merge": "merge"},
    )
    g.add_conditional_edges(
        "analyst",
        after_specialist,
        {"critic": "critic", "merge": "merge"},
    )
    g.add_edge("critic", "merge")
    g.add_edge("merge", END)
    return g.compile()


def run_multi_agent(question: str) -> TeamState:
    app = build_multi_agent()
    return app.invoke(
        {
            "question": question,
            "route": "",
            "writer_out": "",
            "analyst_out": "",
            "critic_out": "",
            "final": "",
            "log": [],
        }
    )
