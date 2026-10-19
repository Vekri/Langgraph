"""
3) Automation — multi-step task with retries.

Pattern: plan → execute step → validate → (retry on fail) → complete.
Simulates a flaky step that succeeds after retries.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

MAX_RETRIES = 3


class AutoState(TypedDict):
    task: str
    steps: list[str]
    current: int
    attempt: int
    log: list[str]
    status: str
    result: str


def plan(state: AutoState) -> dict:
    task = (state.get("task") or "process order").strip()
    steps = [
        f"Validate input for “{task}”",
        "Call downstream service (may fail)",
        "Write result to store",
        "Notify user",
    ]
    return {
        "steps": steps,
        "current": 0,
        "attempt": 0,
        "log": [f"Planned {len(steps)} steps"],
        "status": "planned",
        "result": "",
    }


def execute(state: AutoState) -> dict:
    steps = state["steps"]
    i = state["current"]
    attempt = state.get("attempt", 0) + 1
    log = list(state.get("log") or [])
    step = steps[i]

    # Step 1 (index 1) is flaky: fails until attempt >= 2
    if i == 1 and attempt < 2:
        log.append(f"FAIL step {i + 1}: {step} (attempt {attempt})")
        return {"attempt": attempt, "log": log, "status": "failed"}

    log.append(f"OK   step {i + 1}: {step} (attempt {attempt})")
    return {
        "attempt": 0,  # reset for next step
        "current": i + 1,
        "log": log,
        "status": "running",
    }


def validate(state: AutoState) -> dict:
    if state.get("status") == "failed":
        return {}
    if state["current"] >= len(state["steps"]):
        return {
            "status": "done",
            "result": f"Automation complete for: {state['task']}",
        }
    return {"status": "running"}


def route(state: AutoState) -> Literal["execute", "execute_retry", "__end__"]:
    if state.get("status") == "done":
        return "__end__"
    if state.get("status") == "failed":
        if state.get("attempt", 0) >= MAX_RETRIES:
            return "__end__"
        return "execute_retry"
    if state["current"] >= len(state.get("steps") or []):
        return "__end__"
    return "execute"


def mark_exhausted(state: AutoState) -> dict:
    if state.get("status") == "done":
        return {}
    if state.get("status") == "failed" and state.get("attempt", 0) >= MAX_RETRIES:
        log = list(state.get("log") or [])
        log.append("STOPPED: max retries reached")
        return {"status": "error", "result": "Failed after retries", "log": log}
    return {}


def build_automation():
    g = StateGraph(AutoState)
    g.add_node("plan", plan)
    g.add_node("execute", execute)
    g.add_node("validate", validate)
    g.add_node("exhausted", mark_exhausted)

    g.add_edge(START, "plan")
    g.add_edge("plan", "execute")
    g.add_edge("execute", "validate")
    g.add_conditional_edges(
        "validate",
        route,
        {
            "execute": "execute",
            "execute_retry": "execute",
            "__end__": "exhausted",
        },
    )
    g.add_edge("exhausted", END)
    return g.compile()


def run_automation(task: str) -> AutoState:
    app = build_automation()
    return app.invoke(
        {
            "task": task,
            "steps": [],
            "current": 0,
            "attempt": 0,
            "log": [],
            "status": "started",
            "result": "",
        }
    )
