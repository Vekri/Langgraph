"""
Simple Sample Project: Mini Support Agent (LangGraph)

What it does (no API key needed):
  1. Read the user's message
  2. Decide the category: greeting / billing / tech / unknown
  3. Write a helpful reply
  4. If unknown → ask again (loop once), then end

Install:
    pip install langgraph

Run:
    python support_agent.py
"""

from typing import Literal, TypedDict

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:
    print("Install first:  pip install langgraph")
    raise SystemExit(1)


# ---------- 1) DEFINE STATE (shared memory) ----------
class TicketState(TypedDict):
    message: str
    category: str
    reply: str
    tries: int


# ---------- 2) NODES (units of work) ----------
def understand(state: TicketState) -> TicketState:
    """Normalize the message a bit."""
    text = (state.get("message") or "").strip().lower()
    return {"message": text, "tries": state.get("tries", 0)}


def decide(state: TicketState) -> TicketState:
    """Route the ticket by simple keyword rules."""
    msg = state["message"]
    if any(w in msg for w in ("hi", "hello", "hey")):
        category = "greeting"
    elif any(w in msg for w in ("bill", "invoice", "payment", "refund")):
        category = "billing"
    elif any(w in msg for w in ("error", "bug", "crash", "login", "password")):
        category = "tech"
    else:
        category = "unknown"
    return {"category": category}


def reply_node(state: TicketState) -> TicketState:
    """Write the answer based on category."""
    answers = {
        "greeting": "Hello! How can I help you today?",
        "billing": "For billing, check Settings -> Bills, or email billing@example.com.",
        "tech": "Try restarting the app. If login fails, use 'Forgot password'.",
        "unknown": "Sorry, I did not understand. Please say billing, tech, or hello.",
    }
    return {"reply": answers[state["category"]], "tries": state.get("tries", 0) + 1}


def route_after_reply(state: TicketState) -> Literal["understand", "__end__"]:
    """If unknown and we still have a try left → loop. Else end."""
    if state["category"] == "unknown" and state.get("tries", 0) < 2:
        return "understand"
    return "__end__"


# ---------- 3) EDGES + 4) COMPILE & RUN ----------
def build_app():
    graph = StateGraph(TicketState)

    graph.add_node("understand", understand)
    graph.add_node("decide", decide)
    graph.add_node("reply", reply_node)

    graph.add_edge(START, "understand")
    graph.add_edge("understand", "decide")
    graph.add_edge("decide", "reply")
    graph.add_conditional_edges(
        "reply",
        route_after_reply,
        {"understand": "understand", "__end__": END},
    )

    return graph.compile()


def demo():
    app = build_app()
    examples = [
        "Hello there!",
        "I have a billing question about my invoice",
        "App crash on login",
        "asdf qwerty",  # unknown → one retry path conceptually
    ]

    print("=" * 56)
    print(" SAMPLE PROJECT: Mini Support Agent (LangGraph)")
    print(" Flow: Start -> understand -> decide -> reply -> End")
    print("       (unknown can loop back once)")
    print("=" * 56)

    for msg in examples:
        result = app.invoke({"message": msg, "category": "", "reply": "", "tries": 0})
        print(f"\nUser : {msg}")
        print(f"Route: {result['category']}")
        print(f"Bot  : {result['reply']}")

    print("\n" + "=" * 56)
    print("You just ran: State + Nodes + Edges + Compile. That's LangGraph!")
    print("=" * 56)


if __name__ == "__main__":
    demo()
