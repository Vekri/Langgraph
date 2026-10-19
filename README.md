# LangGraph Tutorial

Beginner-friendly LangGraph code: video tutorial companion, Mini Support Agent sample, and four real-world use-case apps in one place.

## Quick start

```bash
pip install langgraph streamlit
```

### Sample project — Mini Support Agent

```bash
cd sample_project
python support_agent.py
```

### Four use cases (one Streamlit app)

```bash
cd use_cases_app
streamlit run app.py
```

| # | Use case | Pattern |
|---|----------|---------|
| 1 | AI Assistants | remember + act |
| 2 | Research Agents | search → analyze → summarize |
| 3 | Automation | multi-step + retries |
| 4 | Multi-Agent | supervisor → specialists → merge |

### Rebuild the tutorial video (optional)

```bash
pip install pillow imageio imageio-ffmpeg numpy edge-tts
python generate_video.py
```

Then open `index.html` to play `langgraph_tutorial.mp4` with chapters.

## YouTube

See `YOUTUBE_TITLE.txt` and `YOUTUBE_DESCRIPTION.txt` for upload metadata.

## License

MIT
