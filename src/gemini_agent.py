"""Gemini-powered scriptwriter that turns a topic into a narrated Manim scene.

Uses `google-genai` (the new ADK-compatible Gemini SDK). The generated scene
subclasses `VoiceoverScene` from `manim-voiceover`, so animation timing is
auto-synced to TTS narration.

Set GOOGLE_API_KEY in .env before running.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")

SYSTEM_PROMPT = r"""You are an expert at producing 3Blue1Brown-style narrated
explainer videos using Manim Community v0.20+ and the `manim-voiceover` plugin.

Output a SINGLE complete Python file that defines ONE Scene and nothing else.

# REQUIRED IMPORTS (use exactly this header):
```
from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np
```

# REQUIRED STRUCTURE:
```
class <PascalCaseName>(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(voice="Aoede"))
        # ... animations wrapped in `with self.voiceover(...)` blocks ...
```

# VOICE — MANDATORY:
Use ONLY `GeminiTTSService` (Gemini's native AI voice). Do NOT use gTTS,
edge-tts, ElevenLabs, or any other speech service. The voice must be one of:
Aoede (default warm/clear), Puck (lively), Charon (deep), Kore (warm-female),
Fenrir (gravelly), Leda (youthful), Orus (formal-masculine), Zephyr (bright).

# NARRATION RULES (most important):
1. EVERY animation block must be inside a `with self.voiceover(text=...) as tracker:` block.
2. Use `run_time=tracker.duration` so the animation matches the speech length.
3. Narration text should be conversational, 1-3 sentences per block (5-15 seconds).
4. The full video should narrate a complete 60-120 second story.
5. Open with a hook ("Why does pi appear in...?"), explain the intuition step by step,
   end with a satisfying payoff.

# LAYOUT RULES — preventing overlap (critical, this is what was broken before):
A. Define a single CAPTION ZONE: caption mobjects always live near `to_edge(DOWN, buff=0.5)`.
   When a new caption appears, ALWAYS `FadeOut` the previous one in the SAME play call,
   or use `Transform(old_caption, new_caption)`.
B. Define a TITLE ZONE at `to_edge(UP, buff=0.5)` reserved for the section title.
C. The CENTER zone holds the primary visualization. Before introducing a new
   visualization in the center, FadeOut the previous center group:
       `self.play(FadeOut(VGroup(*self.mobjects)))`  # nuclear option, OK between sections
   …or track them in a `current_group` VGroup and fade just that.
D. Use `.next_to(other, DOWN, buff=0.5)` with explicit buff. NEVER overlap mobjects.
E. When transforming an equation in place, use `TransformMatchingTex(old, new)` and
   keep both at the same position.
F. After every section, ensure on-screen mobject count is small. Don't accumulate.
G. Use `font_size=28` for body text, `font_size=36` for equations, `font_size=42` for titles.
   These sizes prevent overflow.
H. Wrap long captions: keep each Text under ~60 characters; break long ones into two
   stacked lines with `VGroup(line1, line2).arrange(DOWN, buff=0.15)`.

# MANIM API GOTCHAS (Manim Community v0.20+) — STRICT, violations break rendering:
- `Indicate(mob, scale_factor=1.5)` — NEVER `scale=...`. Same for `Circumscribe`.
- `Circumscribe(mob, color=YELLOW)` — only `color`, `shape`, `time_width`. NO `fade_out`.
- `FadeIn`/`FadeOut` accept `shift=` only. NEVER `scale=`.
- `Circle(radius=1, color=BLUE)` — never pass `angle=`. Use `Arc` for partials.
- `Axes(x_range=[-3, 3, 1], y_range=[0, 1, 0.25])` — lists, not tuples.
- Plot with `axes.plot(lambda x: ..., color=BLUE)`.
- Use raw strings for ALL LaTeX: `MathTex(r"\pi")`, never `"\pi"`.
- Keep LaTeX simple — amsmath only: `^`, `_`, `\frac`, `\int`, `\sum`, `\pi`, `\sqrt`, `\cdot`.
- DO NOT use `get_part_by_tex` or `get_parts_by_tex` AT ALL. To highlight a
  symbol, pass it as a SEPARATE argument: `MathTex(r"f(x) = ", r"\pi", r"...")`
  then index `formula[1]`. Or just `Indicate(whole_formula)`.
- Use named colors only: BLUE, YELLOW, RED, GREEN, WHITE, ORANGE, PURPLE, GREY, TEAL.
- Do NOT define helper lambdas like `caption_zone = lambda mob: mob.to_edge(...)`.
  Just call `.to_edge(DOWN, buff=0.5)` directly on each mobject.
- For text positioning use `.to_edge(UP/DOWN, buff=0.5)`, `.to_corner(UR)`,
  `.next_to(other, DOWN, buff=0.4)`, or `.move_to(ORIGIN)` directly.

# OUTPUT FORMAT:
Return ONLY the Python code. No markdown fences. No commentary. No leading text.
The first line must be `from manim import *`.
"""


@dataclass
class SceneScript:
    code: str
    scene_class: str


def _extract_scene_class(code: str) -> str:
    m = re.search(r"class\s+(\w+)\s*\(\s*VoiceoverScene\s*\)", code)
    if m:
        return m.group(1)
    m = re.search(r"class\s+(\w+)\s*\(\s*Scene\s*\)", code)
    return m.group(1) if m else "GeneratedScene"


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def normalize_tts_to_gemini(code: str) -> str:
    """Rewrite any non-Gemini speech service to GeminiTTSService.

    The TTS contract for this project is "always Gemini AI voice". If the
    model regresses and emits gTTS / edge-tts / ElevenLabs imports, we rewrite
    them deterministically here so the rendered scene still uses Gemini TTS.
    """
    # gTTS
    code = re.sub(
        r"from\s+manim_voiceover\.services\.gtts\s+import\s+GTTSService",
        "from src.agents.tts import GeminiTTSService",
        code,
    )
    code = re.sub(r"GTTSService\([^)]*\)", 'GeminiTTSService(voice="Aoede")', code)
    # edge-tts
    code = re.sub(
        r"from\s+manim_voiceover\.services\.edge_tts\s+import\s+\w+",
        "from src.agents.tts import GeminiTTSService",
        code,
    )
    code = re.sub(r"EdgeTTSService\([^)]*\)", 'GeminiTTSService(voice="Aoede")', code)
    # ElevenLabs
    code = re.sub(
        r"from\s+manim_voiceover\.services\.elevenlabs\s+import\s+\w+",
        "from src.agents.tts import GeminiTTSService",
        code,
    )
    code = re.sub(r"ElevenLabsService\([^)]*\)", 'GeminiTTSService(voice="Aoede")', code)
    return code


def _gen(client, model: str, contents, system: str) -> str:
    from google.genai import types

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system),
    )
    return _strip_fences(response.text or "")


def generate_scene(topic: str, model: str = DEFAULT_MODEL) -> SceneScript:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set. Add it to .env.")

    from google import genai

    client = genai.Client(api_key=api_key)
    code = _gen(client, model, f"Topic: {topic}", SYSTEM_PROMPT)
    code = normalize_tts_to_gemini(code)
    return SceneScript(code=code, scene_class=_extract_scene_class(code))


def repair_scene(broken_code: str, error_text: str,
                 model: str = DEFAULT_MODEL) -> SceneScript:
    """Ask Gemini to fix its own broken scene given the runtime error."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set.")

    from google import genai

    client = genai.Client(api_key=api_key)
    repair_instruction = (
        SYSTEM_PROMPT
        + "\n\n# REPAIR MODE\n"
        "The previous code you generated failed to render. Below is the code"
        " followed by the error trace. Output a CORRECTED full file that fixes"
        " the error. Keep the same Scene class name. Output ONLY the Python"
        " code, no commentary."
    )
    contents = (
        f"--- BROKEN CODE ---\n{broken_code}\n\n"
        f"--- ERROR ---\n{error_text[-3000:]}\n\n"
        "Now output the corrected full file."
    )
    code = _gen(client, model, contents, repair_instruction)
    code = normalize_tts_to_gemini(code)
    return SceneScript(code=code, scene_class=_extract_scene_class(code))


def save_scene(script: SceneScript, out_dir: Path | str = "scenes") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{script.scene_class.lower()}.py"
    path.write_text(script.code)
    return path
