"""
Create a best-in-class YouTube Short for LangGraph (9:16, under 60s, with voice).

Run:
    python generate_short.py

Output:
    langgraph_short.mp4
    SHORT_YOUTUBE_TITLE.txt
    SHORT_YOUTUBE_DESCRIPTION.txt
"""

from __future__ import annotations

import asyncio
import math
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "langgraph_short.mp4"
TITLE_FILE = HERE / "SHORT_YOUTUBE_TITLE.txt"
DESC_FILE = HERE / "SHORT_YOUTUBE_DESCRIPTION.txt"

# YouTube Shorts: vertical HD
W, H = 1080, 1920
FPS = 24
VOICE = "en-US-JennyNeural"

TEAL = (15, 118, 110)
TEAL_B = (20, 184, 166)
INK = (11, 36, 48)
SOFT = (61, 90, 102)
WHITE = (255, 255, 255)
MINT = (204, 251, 241)
DARK = (11, 36, 48)

SHORT_TITLE = "Stop building dumb AI agents. Use LangGraph 🔥"

SHORT_DESC = """Stop one-shot chatbots. Build agents that remember, decide, and retry.

LangGraph in 50 seconds:
• Nodes = work
• Edges = flow
• State = memory
• Cycles = retry until done

▶ Full tutorial:
LangGraph Tutorial for Beginners | Build AI Agents with Graphs (Sample Project Included)
https://www.youtube.com/watch?v=6zHbVkJL4E0

📦 Code on GitHub:
https://github.com/Vekri/Langgraph

#LangGraph #AIAgents #LangChain #Python #Shorts #AgenticAI #AI #Coding
"""

# Punchy Short beats — hook first
SCENES = [
    {
        "id": "hook",
        "speak": "Stop building dumb AI agents.",
        "big": "STOP building\ndumb AI agents",
        "sub": "",
    },
    {
        "id": "pain",
        "speak": "One long chat loop. No memory. No retries. No control.",
        "big": "Chat loops\nbreak in production",
        "sub": "forget · fail · no retry",
    },
    {
        "id": "reveal",
        "speak": "Use LangGraph. Build agents as graphs.",
        "big": "Use LangGraph",
        "sub": "Stateful AI agents as graphs",
    },
    {
        "id": "blocks",
        "speak": "Node is work. Edge is flow. State is memory. Cycles let you retry.",
        "big": "4 words",
        "sub": "Node · Edge · State · Cycle",
    },
    {
        "id": "loop",
        "speak": "Understand. Decide. Act. Loop until the goal is done.",
        "big": "Understand → Decide\n→ Act → Loop",
        "sub": "That is the magic",
    },
    {
        "id": "cta",
        "speak": "Code on GitHub. Link in bio. Follow for the full tutorial.",
        "big": "Code on GitHub",
        "sub": "github.com/Vekri/Langgraph",
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
    top = np.array([232, 250, 245], dtype=np.float32)
    bot = np.array([15, 118, 110], dtype=np.float32) * 0.15 + np.array([220, 245, 240], dtype=np.float32) * 0.85
    base = top * (1 - t[..., None]) + bot * t[..., None]
    # soft glow top-right
    gx = (xx.astype(np.float32) / W - 0.7) ** 2
    gy = (yy.astype(np.float32) / H - 0.15) ** 2
    glow = np.exp(-(gx + gy) / 0.12)[..., None]
    rgb = np.clip(base + glow * np.array([40, 55, 45], dtype=np.float32), 0, 255).astype(np.uint8)
    img = Image.fromarray(rgb, "RGB")
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(0, H, 64):
        d.line([(0, y), (W, y)], fill=(15, 118, 110, 18), width=1)
    for x in range(0, W, 64):
        d.line([(x, 0), (x, H)], fill=(15, 118, 110, 18), width=1)
    return img


BG = None
F_BRAND = F_BIG = F_SUB = F_CAPTION = F_SMALL = None


def init_fonts():
    global BG, F_BRAND, F_BIG, F_SUB, F_CAPTION, F_SMALL
    BG = make_bg()
    F_BRAND = font(36, True)
    F_BIG = font(78, True)
    F_SUB = font(40, True)
    F_CAPTION = font(34)
    F_SMALL = font(28, True)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.replace("\n", " \n ").split(), [], ""
    for w in words:
        if w == "\n":
            if cur:
                lines.append(cur)
            cur = ""
            continue
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


def draw_progress(d, scene_i, local_pct, total):
    pct = (scene_i + local_pct) / total
    y = 48
    d.rounded_rectangle([80, y, W - 80, y + 10], 5, fill=(11, 36, 48, 40))
    d.rounded_rectangle([80, y, 80 + max(8, int((W - 160) * pct)), y + 10], 5, fill=TEAL_B)


def draw_caption_bar(d, speak: str):
    # Safe-area caption for Shorts (above bottom UI)
    box_y = H - 340
    d.rounded_rectangle([48, box_y, W - 48, H - 160], 24, fill=(11, 36, 48, 210))
    y = box_y + 28
    for line in wrap(d, speak, F_CAPTION, W - 120)[:4]:
        tw = d.textlength(line, font=F_CAPTION)
        d.text(((W - tw) / 2, y), line, fill=WHITE, font=F_CAPTION)
        y += 42


def centered_multiline(d, text, fnt, y_start, fill, max_w=W - 120, gap=10):
    lines = []
    for part in text.split("\n"):
        lines.extend(wrap(d, part, fnt, max_w) or [""])
    y = y_start
    for line in lines:
        tw = d.textlength(line, font=fnt)
        d.text(((W - tw) / 2, y), line, fill=fill, font=fnt)
        y += fnt.size + gap
    return y


def frame_hook(pct, total, scene_i, speak):
    img = BG.copy()
    d = ImageDraw.Draw(img, "RGBA")
    draw_progress(d, scene_i, pct, total)
    d.text((80, 90), "LANGGRAPH  ·  SHORT", fill=TEAL, font=F_BRAND)
    # pulse scale feel via slight vertical offset
    y = 520 + int(8 * math.sin(pct * math.pi))
    centered_multiline(d, "STOP building\ndumb AI agents", F_BIG, y, INK, gap=14)
    draw_caption_bar(d, speak)
    return np.asarray(img)


def frame_pain(pct, total, scene_i, speak):
    img = BG.copy()
    d = ImageDraw.Draw(img, "RGBA")
    draw_progress(d, scene_i, pct, total)
    d.text((80, 90), "THE PROBLEM", fill=TEAL, font=F_BRAND)
    centered_multiline(d, "Chat loops\nbreak in\nproduction", F_BIG, 420, INK, gap=12)
    pills = ["no memory", "no retries", "no control"]
    show = min(3, 1 + int(pct * 3))
    y = 980
    for i, p in enumerate(pills[:show]):
        tw = d.textlength(p, font=F_SUB)
        x0 = (W - tw) / 2 - 28
        d.rounded_rectangle([x0, y, x0 + tw + 56, y + 64], 32, fill=WHITE, outline=TEAL, width=3)
        d.text((x0 + 28, y + 12), p, fill=TEAL, font=F_SUB)
        y += 90
    draw_caption_bar(d, speak)
    return np.asarray(img)


def frame_reveal(pct, total, scene_i, speak):
    img = BG.copy()
    d = ImageDraw.Draw(img, "RGBA")
    draw_progress(d, scene_i, pct, total)
    d.text((80, 90), "THE FIX", fill=TEAL, font=F_BRAND)
    # graph core
    cx, cy, r = W // 2, 780, 210
    for i, lab in enumerate(["Node", "Edge", "State", "Loop"]):
        ang = math.radians(-90 + i * 90 + pct * 40)
        x = cx + int(math.cos(ang) * r)
        y = cy + int(math.sin(ang) * r)
        d.rounded_rectangle([x - 70, y - 36, x + 70, y + 36], 20, fill=WHITE, outline=TEAL, width=3)
        tw = d.textlength(lab, font=F_SMALL)
        d.text((x - tw / 2, y - 16), lab, fill=TEAL, font=F_SMALL)
    d.rounded_rectangle([cx - 110, cy - 70, cx + 110, cy + 70], 28, fill=TEAL)
    tw = d.textlength("LangGraph", font=F_SUB)
    d.text((cx - tw / 2, cy - 24), "LangGraph", fill=WHITE, font=F_SUB)
    centered_multiline(d, "Build agents\nas graphs", F_BIG, 1180, INK, gap=10)
    draw_caption_bar(d, speak)
    return np.asarray(img)


def frame_blocks(pct, total, scene_i, speak):
    img = BG.copy()
    d = ImageDraw.Draw(img, "RGBA")
    draw_progress(d, scene_i, pct, total)
    d.text((80, 90), "REMEMBER THIS", fill=TEAL, font=F_BRAND)
    centered_multiline(d, "4 words", F_BIG, 280, INK)
    items = [
        ("Node", "a unit of work"),
        ("Edge", "what happens next"),
        ("State", "shared memory"),
        ("Cycle", "retry until done"),
    ]
    show = min(4, 1 + int(pct * 4))
    y = 520
    for title, desc in items[:show]:
        d.rounded_rectangle([72, y, W - 72, y + 150], 24, fill=WHITE, outline=(180, 220, 210), width=2)
        d.text((110, y + 28), title, fill=TEAL, font=font(48, True))
        d.text((110, y + 90), desc, fill=SOFT, font=F_SUB)
        y += 175
    draw_caption_bar(d, speak)
    return np.asarray(img)


def frame_loop(pct, total, scene_i, speak):
    img = BG.copy()
    d = ImageDraw.Draw(img, "RGBA")
    draw_progress(d, scene_i, pct, total)
    d.text((80, 90), "THE LOOP", fill=TEAL, font=F_BRAND)
    nodes = ["Start", "Understand", "Decide", "Act", "End"]
    lit = min(4, int(pct * 5))
    y0 = 480
    for i, name in enumerate(nodes):
        on = i <= lit
        tw = d.textlength(name, font=F_SUB)
        d.rounded_rectangle(
            [(W - tw) / 2 - 40, y0, (W + tw) / 2 + 40, y0 + 80],
            40, fill=TEAL if on else WHITE, outline=TEAL, width=3,
        )
        d.text(((W - tw) / 2, y0 + 18), name, fill=WHITE if on else TEAL, font=F_SUB)
        if i < len(nodes) - 1:
            d.text((W / 2 - 12, y0 + 88), "↓", fill=TEAL_B if on else SOFT, font=font(36, True))
        y0 += 130
    if lit >= 3:
        msg = "↺ retry until goal met"
        tw = d.textlength(msg, font=F_SUB)
        d.text(((W - tw) / 2, 1580), msg, fill=TEAL, font=F_SUB)
    draw_caption_bar(d, speak)
    return np.asarray(img)


def frame_cta(pct, total, scene_i, speak):
    img = BG.copy()
    d = ImageDraw.Draw(img, "RGBA")
    draw_progress(d, scene_i, pct, total)
    d.text((80, 90), "NEXT STEP", fill=TEAL, font=F_BRAND)
    centered_multiline(d, "Code on\nGitHub", F_BIG, 520, INK, gap=14)
    link = "github.com/Vekri/Langgraph"
    tw = d.textlength(link, font=F_SUB)
    d.rounded_rectangle([(W - tw) / 2 - 36, 900, (W + tw) / 2 + 36, 980], 24, fill=TEAL)
    d.text(((W - tw) / 2, 918), link, fill=WHITE, font=F_SUB)
    centered_multiline(d, "Follow for the\nfull tutorial", F_SUB, 1100, SOFT, gap=8)
    draw_caption_bar(d, speak)
    return np.asarray(img)


RENDER = {
    "hook": frame_hook,
    "pain": frame_pain,
    "reveal": frame_reveal,
    "blocks": frame_blocks,
    "loop": frame_loop,
    "cta": frame_cta,
}


async def synth(text: str, path: Path):
    await edge_tts.Communicate(text, VOICE, rate="+8%").save(str(path))


def audio_duration(path: Path) -> float:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [ffmpeg, "-i", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", proc.stderr or "")
    if not m:
        return 4.0
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


def render_clip(scene: dict, scene_i: int, total: int, seconds: float, out: Path):
    fn = RENDER[scene["id"]]
    n = max(1, int(seconds * FPS))
    writer = imageio.get_writer(
        str(out), fps=FPS, codec="libx264", quality=8,
        pixelformat="yuv420p", macro_block_size=1,
    )
    try:
        for i in range(n):
            pct = i / max(1, n - 1)
            writer.append_data(fn(pct, total, scene_i, scene["speak"]))
    finally:
        writer.close()


def mux(video: Path, audio: Path, out: Path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-y", "-i", str(video), "-i", str(audio),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)],
        check=True, capture_output=True,
    )


def concat(parts: list[Path], out: Path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    lst = out.parent / "_short_concat.txt"
    lines = [f"file '{p.resolve().as_posix()}'" for p in parts]
    lst.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)],
        check=True, capture_output=True,
    )
    lst.unlink(missing_ok=True)


async def build():
    print("Building LangGraph YouTube Short (9:16)...")
    init_fonts()
    TITLE_FILE.write_text(SHORT_TITLE + "\n", encoding="utf-8")
    DESC_FILE.write_text(SHORT_DESC, encoding="utf-8")

    tmp = Path(tempfile.mkdtemp(prefix="lg_short_"))
    parts = []
    total_len = 0.0
    total = len(SCENES)

    try:
        for i, scene in enumerate(SCENES):
            print(f"[{i+1}/{total}] {scene['id']}")
            audio = tmp / f"a{i}.mp3"
            silent = tmp / f"v{i}.mp4"
            voiced = tmp / f"m{i}.mp4"
            await synth(scene["speak"], audio)
            dur = max(2.8, audio_duration(audio) + 0.35)
            # Keep Short under ~55s total
            render_clip(scene, i, total, dur, silent)
            mux(silent, audio, voiced)
            parts.append(voiced)
            total_len += dur
            print(f"  OK {dur:.1f}s")

        concat(parts, OUT)
        print(f"\nSaved: {OUT}")
        print(f"Length: ~{total_len:.0f}s | {W}x{H} Shorts format")
        print(f"Title: {TITLE_FILE}")
        print(f"Desc:  {DESC_FILE}")
        if total_len > 59:
            print("WARNING: over 60s — trim for Shorts if needed")
    finally:
        for p in tmp.glob("*"):
            try:
                p.unlink()
            except OSError:
                pass
        try:
            tmp.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    asyncio.run(build())
