"""
Chapter 05 — Where people use it
One app · four LangGraph solutions

Run:
    streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents import (  # noqa: E402
    run_assistant,
    run_automation,
    run_multi_agent,
    run_research,
)

st.set_page_config(
    page_title="LangGraph Use Cases",
    page_icon="LG",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;600;700&family=Space+Grotesk:wght@600;700&display=swap');
  html, body, [class*="css"] { font-family: "Instrument Sans", sans-serif; }
  h1, h2, h3 { font-family: "Space Grotesk", sans-serif !important; letter-spacing: -0.02em; }
  .stApp {
    background:
      radial-gradient(ellipse 70% 40% at 0% 0%, #a7f3d0 0%, transparent 50%),
      radial-gradient(ellipse 60% 35% at 100% 0%, #99f6e4 0%, transparent 45%),
      linear-gradient(165deg, #eef8f5 0%, #f7fbfa 50%, #e6f3ef 100%);
  }
  div[data-testid="stSidebar"] {
    background: #0b2430;
  }
  div[data-testid="stSidebar"] * { color: #e7f8f4 !important; }
  .hero {
    background: white; border-radius: 18px; padding: 1.25rem 1.5rem;
    border: 1px solid rgba(15,118,110,.15); margin-bottom: 1rem;
  }
  .hero .eyebrow { color: #0f766e; font-weight: 700; font-size: .8rem; letter-spacing: .12em; text-transform: uppercase; }
  .card {
    background: white; border-radius: 14px; padding: 1rem 1.1rem;
    border: 1px solid rgba(15,118,110,.14); height: 100%;
  }
  .num {
    display: inline-grid; place-items: center; width: 28px; height: 28px;
    border-radius: 8px; background: #ccfbf1; color: #0f766e; font-weight: 700; font-size: .85rem;
  }
  .ok { color: #0f766e; font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)

CASES = {
    "1 · AI Assistants": {
        "blurb": "Chat agents that remember and act.",
        "flow": "understand → (act?) → respond · thread memory",
    },
    "2 · Research Agents": {
        "blurb": "Search, analyze, summarize.",
        "flow": "search → analyze → summarize",
    },
    "3 · Automation": {
        "blurb": "Multi-step tasks with retries.",
        "flow": "plan → execute → validate ↺ retry → done",
    },
    "4 · Multi-Agent": {
        "blurb": "Specialists solving together.",
        "flow": "supervisor → writer|analyst|critic → merge",
    },
}

with st.sidebar:
    st.markdown("### LangGraph Use Cases")
    st.caption("Chapter 05 · Real world · one place")
    choice = st.radio("Choose a solution", list(CASES.keys()), index=0)
    st.divider()
    st.markdown("**Pattern**")
    st.code(CASES[choice]["flow"], language=None)
    st.caption("No API key needed — graph patterns run offline.")

st.markdown(
    f"""
<div class="hero">
  <div class="eyebrow">Chapter 05 · Real world</div>
  <h1 style="margin:.35rem 0 .4rem;color:#0b2430;">Where people use it</h1>
  <p style="margin:0;color:#3d5a66;">{CASES[choice]['blurb']}</p>
</div>
""",
    unsafe_allow_html=True,
)

# Overview cards
c1, c2, c3, c4 = st.columns(4)
for col, (name, meta), n in zip(
    (c1, c2, c3, c4),
    CASES.items(),
    ("1", "2", "3", "4"),
):
    active = name == choice
    with col:
        st.markdown(
            f"""
<div class="card" style="{'outline:2px solid #0f766e;' if active else ''}">
  <span class="num">{n}</span>
  <div style="font-weight:700;margin-top:.45rem;">{name.split(' · ',1)[1]}</div>
  <div style="color:#3d5a66;font-size:.9rem;margin-top:.25rem;">{meta['blurb']}</div>
</div>
""",
            unsafe_allow_html=True,
        )

st.write("")

# --- 1 Assistant ---
if choice.startswith("1"):
    if "asst_history" not in st.session_state:
        st.session_state.asst_history = []

    st.subheader("AI Assistant")
    st.caption("Remembers this chat thread and can call demo tools (weather / time / calc).")

    for m in st.session_state.asst_history:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt = st.chat_input("Try: hello | what's the weather | remind me to ship")
    if prompt:
        st.session_state.asst_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        result = run_assistant(prompt, st.session_state.asst_history[:-1])
        reply = result.get("reply") or ""
        st.session_state.asst_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)
            st.caption(f"Intent: `{result.get('intent')}`")

    if st.button("Clear memory"):
        st.session_state.asst_history = []
        st.rerun()

# --- 2 Research ---
elif choice.startswith("2"):
    st.subheader("Research Agent")
    st.caption("Offline knowledge base: try queries with langgraph, agents, or python.")
    q = st.text_input("Research query", value="What is LangGraph?")
    if st.button("Run research", type="primary"):
        with st.spinner("search → analyze → summarize"):
            out = run_research(q)
        a, b = st.columns(2)
        with a:
            st.markdown("**Sources**")
            for s in out.get("sources") or []:
                st.write(f"• {s}")
        with b:
            st.markdown("**Analysis**")
            for s in out.get("analysis") or []:
                st.write(f"• {s}")
        st.markdown("**Summary**")
        st.success(out.get("summary") or "")

# --- 3 Automation ---
elif choice.startswith("3"):
    st.subheader("Automation")
    st.caption("Step 2 is intentionally flaky — the graph retries until it succeeds.")
    task = st.text_input("Task to automate", value="process refund order #1042")
    if st.button("Run automation", type="primary"):
        with st.spinner("plan → execute → validate (with retries)"):
            out = run_automation(task)
        st.markdown(f"**Status:** `{out.get('status')}`")
        if out.get("result"):
            st.success(out["result"])
        st.markdown("**Run log**")
        for line in out.get("log") or []:
            if line.startswith("FAIL"):
                st.error(line)
            elif line.startswith("OK"):
                st.markdown(f'<span class="ok">{line}</span>', unsafe_allow_html=True)
            else:
                st.write(line)

# --- 4 Multi-agent ---
else:
    st.subheader("Multi-Agent Team")
    st.caption("Supervisor routes to Writer / Analyst / Critic, then merges.")
    question = st.text_input(
        "Team question",
        value="Analyze metrics for shipping a LangGraph support bot",
    )
    if st.button("Run multi-agent", type="primary"):
        with st.spinner("supervisor → specialists → merge"):
            out = run_multi_agent(question)
        st.markdown(f"**Route:** `{out.get('route')}`")
        st.markdown("**Collaboration log**")
        for line in out.get("log") or []:
            st.write(f"• {line}")
        st.markdown("**Final team answer**")
        st.info(out.get("final") or "")

st.divider()
st.caption(
    "Best-practice patterns: typed state · nodes · conditional edges · retries · supervisor routing. "
    "Code lives in `use_cases_app/agents/`."
)
