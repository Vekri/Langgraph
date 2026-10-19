"""
Build langgraph_tutorial.mp4 WITH VOICE from tutorial scenes + sample project.

Requires: pillow, imageio, imageio-ffmpeg, numpy, edge-tts
    pip install pillow imageio imageio-ffmpeg numpy edge-tts

Run:
    python generate_video.py
"""

from __future__ import annotations

import asyncio
import json
import math
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "langgraph_tutorial.mp4"
CHAPTERS_JS = HERE / "chapters.js"
W, H = 1280, 720
FPS = 12
VOICE = "en-US-JennyNeural"  # clear teaching voice

TEAL = (15, 118, 110)
TEAL_B = (20, 184, 166)
INK = (11, 36, 48)
SOFT = (61, 90, 102)
WHITE = (255, 255, 255)
MINT = (204, 251, 241)
CODE_BG = (11, 36, 48)

# Narration scripts (spoken) — keep simple for everyone
SCENES = [
    {
        "id": "title",
        "title": "Intro · LangGraph Tutorial",
        "speak": (
            "Welcome to the LangGraph tutorial. "
            "In a few minutes, you will understand how to build stateful AI agents using graphs, "
            "and we will build a simple support agent sample project together."
        ),
    },
    {
        "id": "what",
        "title": "01 · What is LangGraph?",
        "speak": (
            "LangGraph models your agent as a graph. "
            "Nodes do the work. Edges choose the path. "
            "State keeps memory as the agent moves from step to step."
        ),
    },
    {
        "id": "features",
        "title": "02 · Five superpowers",
        "speak": (
            "LangGraph is graph based, stateful, supports cycles, "
            "multi agent teamwork, and gives you full control over routing and tools."
        ),
    },
    {
        "id": "blocks",
        "title": "03 · Building blocks",
        "speak": (
            "Remember four words. Node is work. Edge is flow. "
            "State is memory. Entry and End mark the start and finish."
        ),
    },
    {
        "id": "flow",
        "title": "04 · How it runs",
        "speak": (
            "The agent starts, understands the input, decides, updates state, acts, "
            "and can loop back until the goal is done. Then it ends."
        ),
    },
    {
        "id": "usecases",
        "title": "05 · Use cases",
        "speak": (
            "People use LangGraph for AI assistants, research agents, "
            "automation pipelines, and multi agent systems."
        ),
    },
    {
        "id": "steps",
        "title": "06 · Four steps",
        "speak": (
            "Build in four steps. Define state. Add nodes. Add edges. Then compile and run."
        ),
    },
    {
        "id": "minicode",
        "title": "07 · Minimal code",
        "speak": (
            "Here is a tiny example. Define state with a message, add a greet node, "
            "set the entry point, compile, and invoke with Hello LangGraph. "
            "The output becomes Hello LangGraph Hi."
        ),
    },
    {
        "id": "sample_intro",
        "title": "08 · Sample project",
        "speak": (
            "Now a simple sample project: a Mini Support Agent. "
            "It reads a user message, decides if it is greeting, billing, or tech, "
            "then replies. If it does not understand, it can ask again."
        ),
    },
    {
        "id": "sample_flow",
        "title": "09 · Project flow",
        "speak": (
            "The flow is Start, to understand, to decide, to reply, then End. "
            "If the category is unknown, it can loop back to understand one more time. "
            "This is a real cyclic workflow."
        ),
    },
    {
        "id": "sample_code",
        "title": "10 · Project code",
        "speak": (
            "In code, Ticket State stores message, category, reply, and tries. "
            "Three nodes: understand, decide, and reply. "
            "A conditional edge chooses whether to loop or finish."
        ),
    },
    {
        "id": "sample_run",
        "title": "11 · Run examples",
        "speak": (
            "When the user says hello, it routes to greeting. "
            "Invoice goes to billing. Login crash goes to tech. "
            "Run sample_project slash support_agent.py to try it yourself."
        ),
    },
    {
        "id": "recap",
        "title": "12 · Recap",
        "speak": (
            "Great job. Agents are graphs. State is memory. Cycles allow retries. "
            "Build with state, nodes, edges, then compile. "
            "Open the sample project and run it. You now know LangGraph."
        ),
    },
]


def font(size: int, bold: bool = False):
    for path in (
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_bg() -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W]
    t = yy.astype(np.float32) / max(H - 1, 1)
    top = np.array([248, 255, 253], dtype=np.float32)
    bot = np.array([213, 240, 234], dtype=np.float32)
    base = top * (1 - t[..., None]) + bot * t[..., None]
    gx = (xx.astype(np.float32) / W - 0.85) ** 2
    gy = (yy.astype(np.float32) / H - 0.12) ** 2
    glow = np.exp(-(gx + gy) / 0.18)[..., None]
    rgb = np.clip(base + glow * np.array([28, 40, 32], dtype=np.float32), 0, 255).astype(np.uint8)
    img = Image.fromarray(rgb, "RGB")
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, W, 48):
        d.line([(x, 0), (x, H)], fill=(15, 118, 110, 16), width=1)
    for y in range(0, H, 48):
        d.line([(0, y), (W, y)], fill=(15, 118, 110, 16), width=1)
    return img


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class Drawer:
    def __init__(self):
        self.bg = make_bg()
        self.f_eye = font(18, True)
        self.f_h1 = font(54, True)
        self.f_h2 = font(40, True)
        self.f_lead = font(23)
        self.f_body = font(20)
        self.f_small = font(16)
        self.f_card = font(18, True)
        self.f_code = font(15)
        self.f_narr = font(17)

    def base(self):
        return self.bg.copy()

    def caption(self, d, text):
        y0 = H - 100
        d.rounded_rectangle([40, y0 - 16, W - 40, H - 28], 12, fill=(255, 255, 255, 220))
        d.text((56, y0 - 8), "Voice", fill=TEAL, font=font(14, True))
        y = y0 + 12
        for line in wrap(d, text, self.f_narr, W - 120)[:3]:
            d.text((56, y), line, fill=INK, font=self.f_narr)
            y += 22

    def progress(self, d, scene_i, local_pct, total):
        pct = (scene_i + local_pct) / total
        by = H - 18
        d.rounded_rectangle([48, by, W - 48, by + 6], 3, fill=(11, 36, 48, 30))
        d.rounded_rectangle([48, by, 48 + max(6, int((W - 96) * pct)), by + 6], 3, fill=TEAL_B)

    def finish(self, img, scene_i, local_pct, total, speak):
        d = ImageDraw.Draw(img, "RGBA")
        self.caption(d, speak)
        self.progress(d, scene_i, local_pct, total)
        return np.asarray(img)

    def title(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 90), "BEGINNER-FRIENDLY WALKTHROUGH", fill=TEAL, font=self.f_eye)
        d.text((56, 140), "LangGraph Tutorial", fill=INK, font=self.f_h1)
        lead = "Build stateful AI agents with graphs — plus a simple sample project."
        for i, line in enumerate(wrap(d, lead, self.f_lead, 640)):
            d.text((56, 240 + i * 34), line, fill=SOFT, font=self.f_lead)
        cx, cy, r = 980, 290, 120
        for i, lab in enumerate(["Node", "Edge", "State", "Loop"]):
            ang = math.radians(-90 + i * 90)
            x = cx + int(math.cos(ang) * r)
            y = cy + int(math.sin(ang) * r)
            d.rounded_rectangle([x - 38, y - 22, x + 38, y + 22], 14, fill=WHITE, outline=TEAL, width=2)
            tw = d.textlength(lab, font=self.f_small)
            d.text((x - tw / 2, y - 9), lab, fill=TEAL, font=self.f_small)
        d.rounded_rectangle([cx - 48, cy - 34, cx + 48, cy + 34], 16, fill=TEAL)
        d.text((cx - 28, cy - 11), "Graph", fill=WHITE, font=self.f_card)
        return self.finish(img, 0, pct, total, speak)

    def what(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 60), "CHAPTER 01  ·  CONCEPT", fill=TEAL, font=self.f_eye)
        d.text((56, 105), "What is LangGraph?", fill=INK, font=self.f_h2)
        lead = "Design AI agents as a map of steps — not one straight line. Think, decide, act, retry."
        for i, line in enumerate(wrap(d, lead, self.f_lead, 1000)):
            d.text((56, 190 + i * 34), line, fill=SOFT, font=self.f_lead)
        for i, tip in enumerate(["Nodes do the work", "Edges choose the path", "State keeps the memory"]):
            y = 300 + i * 55
            d.rounded_rectangle([56, y, 560, y + 44], 12, fill=WHITE, outline=TEAL, width=2)
            d.text((80, y + 10), f">  {tip}", fill=INK, font=self.f_card)
        return self.finish(img, 1, pct, total, speak)

    def features(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 40), "CHAPTER 02  ·  WHY IT MATTERS", fill=TEAL, font=self.f_eye)
        d.text((56, 78), "Five superpowers", fill=INK, font=self.f_h2)
        feats = [
            ("Graph-Based", "Connected steps"),
            ("Stateful", "Shared memory"),
            ("Cyclic", "Loop & retry"),
            ("Multi-Agent", "Teamwork"),
            ("Full Control", "Your rules"),
        ]
        card_w, gap = 210, 14
        x0 = (W - (5 * card_w + 4 * gap)) // 2
        show = min(5, 1 + int(pct * 5))
        for i, (title, desc) in enumerate(feats[:show]):
            x = x0 + i * (card_w + gap)
            y = 160
            d.rounded_rectangle([x, y, x + card_w, y + 250], 16, fill=WHITE, outline=(180, 220, 210), width=2)
            d.rounded_rectangle([x + 75, y + 28, x + 135, y + 88], 14, fill=MINT)
            d.text((x + 20, y + 120), title, fill=INK, font=self.f_card)
            d.text((x + 20, y + 160), desc, fill=SOFT, font=self.f_small)
        return self.finish(img, 2, pct, total, speak)

    def blocks(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 45), "CHAPTER 03  ·  VOCABULARY", fill=TEAL, font=self.f_eye)
        d.text((56, 85), "Only four building blocks", fill=INK, font=self.f_h2)
        items = [
            ("Node", "A unit of work — a Python function."),
            ("Edge", "What happens next."),
            ("State", "Shared memory for the graph."),
            ("Entry / End", "Start and finish points."),
        ]
        show = min(4, 1 + int(pct * 4))
        for i, (title, desc) in enumerate(items[:show]):
            x = 56 + (i % 2) * 580
            y = 170 + (i // 2) * 155
            d.rounded_rectangle([x, y, x + 540, y + 130], 16, fill=WHITE, outline=(180, 220, 210), width=2)
            d.text((x + 24, y + 24), title, fill=TEAL, font=font(26, True))
            d.text((x + 24, y + 70), desc, fill=SOFT, font=self.f_body)
        return self.finish(img, 3, pct, total, speak)

    def flow(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 45), "CHAPTER 04  ·  THE LOOP", fill=TEAL, font=self.f_eye)
        d.text((56, 85), "How a LangGraph runs", fill=INK, font=self.f_h2)
        nodes = ["Start", "Understand", "Decide", "Update", "Act", "End"]
        lit = min(5, int(pct * 6))
        xs = np.linspace(80, W - 80, len(nodes))
        y = 250
        for i, name in enumerate(nodes):
            on = i <= lit
            tw = d.textlength(name, font=self.f_small)
            pad = 16
            d.rounded_rectangle(
                [xs[i] - tw / 2 - pad, y - 26, xs[i] + tw / 2 + pad, y + 26],
                22, fill=TEAL if on else WHITE, outline=TEAL, width=2,
            )
            d.text((xs[i] - tw / 2, y - 10), name, fill=WHITE if on else TEAL, font=self.f_small)
            if i < len(nodes) - 1:
                d.line([(xs[i] + tw / 2 + pad + 2, y), (xs[i + 1] - 40, y)],
                       fill=TEAL_B if on else (170, 210, 200), width=3)
        if lit >= 4:
            msg = "No / Retry -> back to Understand (cycles!)"
            d.text((W / 2 - d.textlength(msg, font=self.f_body) / 2, 330), msg, fill=TEAL, font=self.f_body)
        return self.finish(img, 4, pct, total, speak)

    def usecases(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 45), "CHAPTER 05  ·  REAL WORLD", fill=TEAL, font=self.f_eye)
        d.text((56, 85), "Where people use it", fill=INK, font=self.f_h2)
        cases = [
            ("1", "AI Assistants", "Chat agents that remember and act"),
            ("2", "Research Agents", "Search, analyze, summarize"),
            ("3", "Automation", "Multi-step tasks with retries"),
            ("4", "Multi-Agent", "Specialists solving together"),
        ]
        show = min(4, 1 + int(pct * 4))
        for i, (num, title, desc) in enumerate(cases[:show]):
            x = 56 + (i % 2) * 580
            y = 170 + (i // 2) * 145
            d.rounded_rectangle([x, y, x + 540, y + 115], 14, fill=WHITE, outline=(180, 220, 210), width=2)
            d.rounded_rectangle([x + 20, y + 34, x + 56, y + 70], 8, fill=MINT)
            d.text((x + 32, y + 40), num, fill=TEAL, font=self.f_card)
            d.text((x + 72, y + 28), title, fill=INK, font=font(24, True))
            d.text((x + 72, y + 68), desc, fill=SOFT, font=self.f_body)
        return self.finish(img, 5, pct, total, speak)

    def steps(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 45), "CHAPTER 06  ·  BUILD PATH", fill=TEAL, font=self.f_eye)
        d.text((56, 85), "Build in 4 simple steps", fill=INK, font=self.f_h2)
        steps = [
            ("1", "Define State", "Shared data schema"),
            ("2", "Add Nodes", "Functions for tasks"),
            ("3", "Add Edges", "Connect the flow"),
            ("4", "Compile & Run", "Make it an app"),
        ]
        d.line([(150, 250), (W - 150, 250)], fill=(20, 184, 166, 90), width=4)
        show = min(4, 1 + int(pct * 4))
        for i, (num, title, desc) in enumerate(steps[:show]):
            x = 170 + i * 280
            d.ellipse([x - 34, 216, x + 34, 284], fill=WHITE, outline=TEAL, width=4)
            tw = d.textlength(num, font=font(26, True))
            d.text((x - tw / 2, 234), num, fill=TEAL, font=font(26, True))
            d.text((x - d.textlength(title, font=self.f_card) / 2, 310), title, fill=INK, font=self.f_card)
            d.text((x - d.textlength(desc, font=self.f_small) / 2, 350), desc, fill=SOFT, font=self.f_small)
        return self.finish(img, 6, pct, total, speak)

    def minicode(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 32), "CHAPTER 07  ·  MINIMAL CODE", fill=TEAL, font=self.f_eye)
        d.text((56, 68), "Your first graph", fill=INK, font=font(36, True))
        code = [
            "from langgraph.graph import StateGraph",
            "class State(TypedDict): message: str",
            "def node(state): return {'message': state['message'] + ' Hi!'}",
            "graph = StateGraph(State)",
            "graph.add_node('greet', node)",
            "app = graph.compile()",
            "app.invoke({'message': 'Hello LangGraph!'})",
            "# -> Hello LangGraph! Hi!",
        ]
        shown = min(len(code), 1 + int(pct * len(code)))
        d.rounded_rectangle([56, 120, W - 56, H - 115], 14, fill=CODE_BG)
        for i, line in enumerate(code[:shown]):
            color = (252, 211, 77) if line.startswith("#") else (209, 250, 229)
            d.text((80, 140 + i * 30), line, fill=color, font=self.f_code)
        return self.finish(img, 7, pct, total, speak)

    def sample_intro(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 50), "CHAPTER 08  ·  SAMPLE PROJECT", fill=TEAL, font=self.f_eye)
        d.text((56, 95), "Mini Support Agent", fill=INK, font=self.f_h2)
        lead = "A tiny real project: route tickets to greeting, billing, or tech — no API key needed."
        for i, line in enumerate(wrap(d, lead, self.f_lead, 1000)):
            d.text((56, 175 + i * 34), line, fill=SOFT, font=self.f_lead)
        for i, (t, s) in enumerate([
            ("Folder", "sample_project/"),
            ("File", "support_agent.py"),
            ("Run", "python support_agent.py"),
        ]):
            y = 280 + i * 60
            d.rounded_rectangle([56, y, 700, y + 50], 12, fill=WHITE, outline=TEAL, width=2)
            d.text((80, y + 12), f"{t}:  {s}", fill=INK, font=self.f_card)
        return self.finish(img, 8, pct, total, speak)

    def sample_flow(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 45), "CHAPTER 09  ·  PROJECT FLOW", fill=TEAL, font=self.f_eye)
        d.text((56, 85), "How the support agent runs", fill=INK, font=self.f_h2)
        nodes = ["Start", "understand", "decide", "reply", "End"]
        lit = min(4, int(pct * 5))
        xs = np.linspace(100, W - 100, len(nodes))
        y = 240
        for i, name in enumerate(nodes):
            on = i <= lit
            tw = d.textlength(name, font=self.f_small)
            pad = 18
            d.rounded_rectangle(
                [xs[i] - tw / 2 - pad, y - 28, xs[i] + tw / 2 + pad, y + 28],
                22, fill=TEAL if on else WHITE, outline=TEAL, width=2,
            )
            d.text((xs[i] - tw / 2, y - 10), name, fill=WHITE if on else TEAL, font=self.f_small)
            if i < len(nodes) - 1:
                d.line([(xs[i] + tw / 2 + pad + 2, y), (xs[i + 1] - 45, y)],
                       fill=TEAL_B if on else (170, 210, 200), width=3)
        if lit >= 3:
            msg = "If unknown -> loop back to understand (once)"
            d.text((W / 2 - d.textlength(msg, font=self.f_body) / 2, 330), msg, fill=TEAL, font=self.f_body)
        return self.finish(img, 9, pct, total, speak)

    def sample_code(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 32), "CHAPTER 10  ·  PROJECT CODE", fill=TEAL, font=self.f_eye)
        d.text((56, 68), "State + Nodes + Edges", fill=INK, font=font(36, True))
        code = [
            "class TicketState(TypedDict):",
            "    message, category, reply, tries",
            "",
            "nodes: understand -> decide -> reply",
            "",
            "if category == 'unknown' and tries < 2:",
            "    go back to understand",
            "else:",
            "    END",
        ]
        shown = min(len(code), 1 + int(pct * len(code)))
        d.rounded_rectangle([56, 120, W - 56, H - 115], 14, fill=CODE_BG)
        for i, line in enumerate(code[:shown]):
            d.text((80, 140 + i * 32), line or " ", fill=(209, 250, 229), font=self.f_code)
        return self.finish(img, 10, pct, total, speak)

    def sample_run(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 40), "CHAPTER 11  ·  RUN EXAMPLES", fill=TEAL, font=self.f_eye)
        d.text((56, 78), "What you will see", fill=INK, font=self.f_h2)
        rows = [
            ("Hello there!", "greeting", "Hello! How can I help you today?"),
            ("billing invoice", "billing", "Check Settings → Bills..."),
            ("login crash", "tech", "Try restarting the app..."),
        ]
        show = min(3, 1 + int(pct * 3))
        for i, (user, route, bot) in enumerate(rows[:show]):
            y = 150 + i * 100
            d.rounded_rectangle([56, y, W - 56, y + 88], 14, fill=WHITE, outline=(180, 220, 210), width=2)
            d.text((76, y + 12), f"User: {user}", fill=INK, font=self.f_card)
            d.text((76, y + 42), f"Route: {route}   |   Bot: {bot}", fill=SOFT, font=self.f_body)
        return self.finish(img, 11, pct, total, speak)

    def recap(self, pct, total, speak):
        img = self.base()
        d = ImageDraw.Draw(img, "RGBA")
        d.text((56, 50), "CHAPTER 12  ·  TAKEAWAY", fill=TEAL, font=self.f_eye)
        d.text((56, 90), "You now know LangGraph", fill=INK, font=self.f_h2)
        points = [
            "Agents are graphs of nodes + edges",
            "State is shared memory",
            "Cycles let agents retry",
            "Try: sample_project/support_agent.py",
        ]
        show = min(4, 1 + int(pct * 4))
        for i, p in enumerate(points[:show]):
            y = 175 + i * 68
            d.rounded_rectangle([56, y, W - 56, y + 52], 12, fill=WHITE)
            d.rectangle([56, y, 68, y + 52], fill=TEAL)
            d.text((90, y + 14), p, fill=INK, font=self.f_lead)
        return self.finish(img, 12, pct, total, speak)


RENDERERS = {
    "title": "title",
    "what": "what",
    "features": "features",
    "blocks": "blocks",
    "flow": "flow",
    "usecases": "usecases",
    "steps": "steps",
    "minicode": "minicode",
    "sample_intro": "sample_intro",
    "sample_flow": "sample_flow",
    "sample_code": "sample_code",
    "sample_run": "sample_run",
    "recap": "recap",
}


async def synth_voice(text: str, out_mp3: Path):
    communicate = edge_tts.Communicate(text, VOICE, rate="-5%")
    await communicate.save(str(out_mp3))


def audio_duration(path: Path) -> float:
    """Duration via ffprobe-like read through ffmpeg."""
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    # Use ffprobe if bundled naming; imageio-ffmpeg is ffmpeg binary.
    # Fallback: decode with imageio
    try:
        reader = imageio.get_reader(str(path))
        meta = reader.get_meta_data()
        reader.close()
        if "duration" in meta and meta["duration"]:
            return float(meta["duration"])
    except Exception:
        pass
    # Parse with ffmpeg -i
    proc = subprocess.run(
        [ffmpeg, "-i", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    import re
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", proc.stderr or "")
    if not m:
        return 5.0
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


def render_scene_video(drawer: Drawer, scene: dict, scene_i: int, total: int, seconds: float, out_mp4: Path):
    method = getattr(drawer, RENDERERS[scene["id"]])
    n = max(1, int(seconds * FPS))
    writer = imageio.get_writer(
        str(out_mp4), fps=FPS, codec="libx264", quality=8,
        pixelformat="yuv420p", macro_block_size=1,
    )
    try:
        for i in range(n):
            pct = i / max(1, n - 1)
            frame = method(pct, total, scene["speak"])
            writer.append_data(frame)
    finally:
        writer.close()


def mux(video: Path, audio: Path, out: Path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-i", str(video),
        "-i", str(audio),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def concat_mp4(parts: list[Path], out: Path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    lst = out.parent / "_concat_list.txt"
    # ffmpeg concat demuxer needs forward slashes / escaped paths
    lines = []
    for p in parts:
        path = p.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{path}'")
    lst.write_text("\n".join(lines), encoding="utf-8")
    cmd = [
        ffmpeg, "-y", "-f", "concat", "-safe", "0",
        "-i", str(lst),
        "-c", "copy",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    lst.unlink(missing_ok=True)


async def build():
    print("LangGraph tutorial video + voice + sample project")
    print(f"Voice: {VOICE}")
    print(f"Output: {OUT}\n")

    drawer = Drawer()
    total = len(SCENES)
    tmp = Path(tempfile.mkdtemp(prefix="lg_vid_"))
    chapter_meta = []
    muxed_parts = []
    t_cursor = 0.0

    try:
        for i, scene in enumerate(SCENES):
            print(f"[{i+1}/{total}] {scene['title']}")
            audio = tmp / f"a_{i:02d}.mp3"
            silent = tmp / f"v_{i:02d}.mp4"
            voiced = tmp / f"m_{i:02d}.mp4"

            print("  - voice...")
            await synth_voice(scene["speak"], audio)
            dur = audio_duration(audio) + 0.6  # small pad after speech
            dur = max(dur, 4.0)

            print(f"  - video ({dur:.1f}s)...")
            render_scene_video(drawer, scene, i, total, dur, silent)

            print("  - mux...")
            mux(silent, audio, voiced)
            muxed_parts.append(voiced)

            chapter_meta.append({
                "title": scene["title"],
                "start": round(t_cursor, 2),
                "duration": round(dur, 2),
            })
            t_cursor += dur
            print("  OK")

        print("\nConcatenating scenes...")
        concat_mp4(muxed_parts, OUT)

        CHAPTERS_JS.write_text(
            "window.TUTORIAL_CHAPTERS = " + json.dumps(chapter_meta, indent=2) + ";\n",
            encoding="utf-8",
        )
        print(f"\nSaved video: {OUT}")
        print(f"Saved chapters: {CHAPTERS_JS}")
        print(f"Total length: ~{t_cursor:.0f}s")
    finally:
        # cleanup temp clips
        for p in tmp.glob("*"):
            try:
                p.unlink()
            except OSError:
                pass
        try:
            tmp.rmdir()
        except OSError:
            pass


def main():
    asyncio.run(build())


if __name__ == "__main__":
    main()
