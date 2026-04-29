# Science Communicator

A 3Blue1Brown-style video & animation pipeline. Combines **Manim** for mathematical
animation, **MoviePy/ffmpeg** for editing, **TTS engines** for narration, and the
**Google Agent Development Kit (ADK)** with Gemini for AI-driven script generation
and scene planning.

## Stack

| Layer | Tool |
|-------|------|
| Animation engine | [Manim Community](https://www.manim.community/) |
| Video editing | MoviePy + ffmpeg |
| Narration | edge-tts / gTTS / ElevenLabs |
| AI scripting | Google ADK + Gemini |

## Setup

```bash
# 1. Activate the virtualenv (already created at .venv/)
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. System deps (already present): cairo, pango, ffmpeg
#    For LaTeX-rendered math, install MacTeX or BasicTeX:
brew install --cask mactex-no-gui   # ~4 GB, full
# OR: brew install --cask basictex  # smaller

# 4. Copy env template and add your keys
cp .env.example .env
# edit .env with GOOGLE_API_KEY, etc.
```

## Project layout

```
science-communicator/
├── scenes/        # Manim scene scripts (one .py per video)
├── src/           # Reusable helpers (AI agents, TTS, compositors)
├── scripts/       # CLI entry points (e.g. generate-from-prompt)
├── assets/        # Static images, fonts, sound effects
├── output/        # Rendered videos
├── requirements.txt
└── .env
```

## Quick start — render a sample scene

```bash
manim -pql scenes/example.py SquareToCircle
# -p = preview, -ql = low quality (fast). Use -qh for HD, -qk for 4K.
```

## Generate a video from a prompt (Gemini + Manim)

```bash
python scripts/generate.py "Explain the Fourier transform visually"
```

## Notes

- `manim` (community) and `manimgl` (3B1B's original) are different libraries.
  Default to `manim`; `manimgl` is included for reference.
- LaTeX is required for `MathTex` / `Tex` objects. Without it, use `Text` only.
