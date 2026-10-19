"""
1) AI Assistant — chat agent that remembers and acts.

Pattern: understand → decide (chat | act) → respond
Memory: thread state carries history across turns.
No API key required (rule-based demo of the graph).
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class AssistantState(TypedDict):
    messages: Annotated[list[dict], add_messages]
    intent: str
    action_result: str
    reply: str


def _msg_role(m) -> str:
    if isinstance(m, dict):
        return m.get("role") or ""
    t = getattr(m, "type", None) or getattr(m, "role", None) or ""
    if t in ("human", "user"):
        return "user"
    if t in ("ai", "assistant"):
        return "assistant"
    return str(t)


def _msg_content(m) -> str:
    if isinstance(m, dict):
        return str(m.get("content") or "")
    return str(getattr(m, "content", "") or "")


def _last_user_text(state: AssistantState) -> str:
    for m in reversed(state.get("messages") or []):
        if _msg_role(m) == "user":
            return _msg_content(m).strip()
    return ""


def understand(state: AssistantState) -> dict:
    text = _last_user_text(state).lower()
    if any(w in text for w in ("remind", "remember", "note")):
        intent = "remember"
    elif any(w in text for w in ("weather", "time", "calculate", "calc", "+")):
        intent = "act"
    elif any(w in text for w in ("hi", "hello", "hey")):
        intent = "greet"
    else:
        intent = "chat"
    return {"intent": intent}


def act(state: AssistantState) -> dict:
    text = _last_user_text(state).lower()
    if "weather" in text:
        result = "Tool: weather → Sunny, 28°C in your city (demo)."
    elif "time" in text:
        from datetime import datetime

        result = f"Tool: clock → {datetime.now().strftime('%I:%M %p')} (local)."
    elif "calc" in text or "+" in text:
        result = "Tool: calculator → 2 + 2 = 4 (demo)."
    else:
        result = "Tool: notepad → saved your note for this thread."
    return {"action_result": result}


def respond(state: AssistantState) -> dict:
    intent = state.get("intent", "chat")
    user = _last_user_text(state)
    history_n = len([m for m in state.get("messages") or [] if _msg_role(m) == "user"])

    if intent == "greet":
        reply = "Hi! I'm your LangGraph assistant. I remember this chat and can take actions."
    elif intent == "act":
        reply = f"{state.get('action_result', '')}\n\nAnything else?"
    elif intent == "remember":
        reply = f"Got it — I'll keep that in mind for this conversation. (turn {history_n})"
    else:
        reply = (
            f"You said: “{user}”. "
            f"I still remember {history_n} user message(s) in this thread. "
            "Try: hello | what's the weather | remind me to ship"
        )

    return {
        "reply": reply,
        "messages": [{"role": "assistant", "content": reply}],
    }


def route(state: AssistantState) -> Literal["act", "respond"]:
    return "act" if state.get("intent") == "act" else "respond"


def build_assistant():
    g = StateGraph(AssistantState)
    g.add_node("understand", understand)
    g.add_node("act", act)
    g.add_node("respond", respond)

    g.add_edge(START, "understand")
    g.add_conditional_edges("understand", route, {"act": "act", "respond": "respond"})
    g.add_edge("act", "respond")
    g.add_edge("respond", END)
    return g.compile()


def run_assistant(user_text: str, history: list[dict] | None = None) -> AssistantState:
    app = build_assistant()
    messages = list(history or [])
    messages.append({"role": "user", "content": user_text})
    return app.invoke(
        {
            "messages": messages,
            "intent": "",
            "action_result": "",
            "reply": "",
        }
    )
