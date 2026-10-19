"""
Minimal LangGraph example from the tutorial.

Install once:
    pip install langgraph

Run:
    python demo.py
"""

from typing import TypedDict

try:
    from langgraph.graph import StateGraph, END
except ImportError:
    print("Install LangGraph first:  pip install langgraph")
    raise SystemExit(1)


class State(TypedDict):
    message: str


def greet(state: State) -> State:
    """Node: one unit of work."""
    return {"message": state["message"] + " Hi!"}


def main() -> None:
    graph = StateGraph(State)
    graph.add_node("greet", greet)
    graph.set_entry_point("greet")
    graph.add_edge("greet", END)

    app = graph.compile()
    result = app.invoke({"message": "Hello LangGraph!"})

    print("=" * 48)
    print("LangGraph mini demo")
    print("=" * 48)
    print("Input :", {"message": "Hello LangGraph!"})
    print("Output:", result)
    print()
    print("Flow  : Start → greet (node) → End")
    print("State was updated by the node. That's LangGraph!")


if __name__ == "__main__":
    main()
