"""Prompt templates for the planner, worker, judge, and QA agents."""

from __future__ import annotations

from src.gemini_agent import SYSTEM_PROMPT as _BASE_WORKER_PROMPT


# ---------------------------------------------------------------------------
# Master planner
# ---------------------------------------------------------------------------

MASTER_PLANNER_PROMPT = r"""You are the master planner for a 3Blue1Brown-style
narrated math/science explainer video. The user gives you a topic. You output
a structured ScenePlan in JSON — no commentary, no markdown.

# YOUR JOB

1. Pick a clear, specific TITLE (5-8 words).
2. Choose total_target_seconds in 60-150 (longer for richer topics).
3. Decompose into 3-7 SCENES. Each scene has a focused goal that fits in 8-30 seconds.
4. For each scene, decide complexity:
   - "simple": one tight visualization, 2-4 narration beats. Use this by default.
   - "complex": ONLY when the visualization needs a multi-step transformation
     that's hard to verify in one render (e.g. "concentric rings unrolled into
     a triangle", "Fourier series approximating a square wave at N=1,3,5,9").
5. For "simple" scenes, populate `beats` (a list of NarrationBeat). Each beat:
     - text: the EXACT narrator sentence(s), 1-2 sentences. Conversational,
       intuitive, natural. The TTS will speak this verbatim.
     - animation_hint: what should be on screen during this beat. Be concrete:
       "draw a blue circle of radius 2 at center", "fade in the formula
       'A = pi r^2' below the circle".
6. For "complex" scenes, populate `sub_scenes` instead of `beats`. 2-4 sub-scenes,
   each with its own beats, key_visuals, target_seconds, and correctness_checks.
   Sub-scenes will be rendered as separate clips and concatenated.
7. ALWAYS populate `correctness_checks` — a checklist of concrete claims a
   visual reviewer can verify by looking at the rendered video. Examples:
     - "the resulting shape is a triangle, not a parallelogram"
     - "the title 'Euler's identity' is at the top of the screen and does not
       overlap the formula"
     - "the curve passes through the point (0, 1)"
     - "the narration in beat 2 mentions 'pi' and the symbol pi is highlighted"
   These checks are how the system gates whether a scene is acceptable.
8. Pick a `voice` from: Aoede (warm/clear, default), Puck (lively), Charon
   (deep/serious), Kore (warm-female), Fenrir (gravelly), Leda (youthful),
   Orus (formal-masculine), Zephyr (bright). Match the topic's tone.

# CONSTRAINTS

- Beat text is VERBATIM TTS. Do not include stage directions, parentheticals,
  or markdown formatting. Use plain prose. Do not say "let's see" too many times.
- Keep beat text under ~50 words. Long beats sound rushed when synced to animation.
- Total of all scene `target_seconds` should equal `total_target_seconds` ± 10%.
- Scene `id` is zero-padded: "01", "02", ... Sub-scene `id` is a single letter:
  "a", "b", "c", "d".
- `slug` is lowercase snake_case ASCII; the worker will convert it to a Manim
  class name (e.g. "concentric_rings" -> "ConcentricRings").
- Sub-scene slug is its own (the runner combines with parent for filenames).
- key_visuals: 2-5 short bullet phrases describing the main mobjects.

# QUALITY EXPECTATIONS

- The narrative should HOOK in scene 1 (a question, a surprising fact).
- Each subsequent scene should advance one idea, with a payoff at the end.
- Avoid jargon without intuition. If you must introduce an equation, narrate
  what each symbol means in plain words.

Output ONLY a valid JSON object matching the ScenePlan schema. No prose, no fences.
"""


# ---------------------------------------------------------------------------
# Worker (per-scene code generator)
# ---------------------------------------------------------------------------

# We start from the existing battle-tested prompt (layout zones, raw-string
# LaTeX, banned API patterns) and append a scene-specific brief. The worker
# emits a single VoiceoverScene file using GeminiTTSService.

_WORKER_HEADER_OVERRIDE = r"""
# REQUIRED IMPORTS for multi-agent runs (replaces the GTTSService import in
# the base instructions above):
```
from manim import *
from manim_voiceover import VoiceoverScene
from src.agents.tts import GeminiTTSService
import numpy as np
```

# SET SPEECH SERVICE — MANDATORY FIRST LINE OF construct():
```
self.set_speech_service(GeminiTTSService(voice="<plan.voice>"))
```

# BEAT FAITHFULNESS — MANDATORY:
- For each beat in the scene plan, emit ONE `with self.voiceover(text=beat.text) as tracker:` block, in order.
- The `text` argument is the beat's `text` field VERBATIM. Do not paraphrase, summarise,
  or rewrite. Preserve punctuation. The TTS will speak exactly what you put there.
- Inside each block, build the animation matching `animation_hint` and end every
  `self.play(...)` with `run_time=tracker.duration`.
- Do not add `self.wait(...)` calls between beats unless explicitly requested
  in the animation_hint — the voiceover blocks already wait on the audio.

# CORRECTNESS CHECKS:
- The plan ships a list of `correctness_checks`. Treat them as ACCEPTANCE
  CRITERIA. The rendered scene must satisfy every check.
- A separate vision-based judge will inspect the rendered output. If it spots
  a violation, you will be asked to fix it on the next iteration.
"""

WORKER_SCENE_PROMPT = _BASE_WORKER_PROMPT + "\n\n" + _WORKER_HEADER_OVERRIDE


def build_worker_user_message(item, parent_plan, sub_scene=None) -> str:
    """Compose the per-scene user message for the worker.

    Either renders a top-level simple scene (sub_scene=None) or a sub-scene of
    a complex scene (sub_scene provided).
    """
    target = sub_scene if sub_scene is not None else item
    beats = target.beats or []
    beat_lines = "\n".join(
        f"  Beat {i+1}: text='{b.text}' | animation_hint='{b.animation_hint}'"
        for i, b in enumerate(beats)
    )
    checks = "\n".join(f"  - {c}" for c in (target.correctness_checks or []))
    visuals = "\n".join(f"  - {v}" for v in (target.key_visuals or []))
    voice = parent_plan.voice
    scene_class = target.scene_class if hasattr(target, "scene_class") else _slug_pascal(target.slug)
    return f"""SCENE BRIEF
Topic of the whole video: {parent_plan.topic}
Title: {parent_plan.title}

This scene class name MUST be: {scene_class}
This scene's description: {target.description}
Target duration: ~{target.target_seconds:.1f} seconds
Voice: {voice}

Key visuals:
{visuals or '  (none)'}

Narration beats (use text VERBATIM, in order):
{beat_lines or '  (none — emit no voiceover blocks)'}

Correctness checks the rendered video MUST satisfy:
{checks or '  (none)'}

Now output the complete Python file for this scene."""


def _slug_pascal(slug: str) -> str:
    parts = slug.replace("__", "_").split("_")
    return "".join(p.capitalize() for p in parts if p)


# ---------------------------------------------------------------------------
# Judge
# ---------------------------------------------------------------------------

JUDGE_PROMPT = r"""You are the quality-gate judge for a 3Blue1Brown-style
explainer scene. The user gives you:

  1. The scene plan (description, beats, key_visuals, correctness_checks).
  2. N frames sampled in chronological order from the rendered scene.
  3. The narration text that was actually spoken (per beat).
  4. The measured scene duration vs the target.

You must decide whether the scene meets ALL of the following:

  A. NO overlapping or clipped text. Title, captions, and equations stay in
     their assigned zones (UP / DOWN / center). Nothing is cut off the edge.
  B. GEOMETRIC CORRECTNESS — every shape is what the description says it is.
     A "triangle" must have three straight sides. "Concentric rings" must
     be circular. A "graph of e^{-x^2}" must look like a bell curve. Call out
     parallelograms, blobs, broken polygons, or misaligned strips.
  C. NARRATION MATCH — the on-screen content during each beat is consistent
     with the beat's text. If the beat says "we now multiply both sides", the
     visible state should reflect that step.
  D. DURATION — total duration is within ±25% of target_seconds.
  E. CORRECTNESS CHECKS — every check in the scene's `correctness_checks`
     list is satisfied.

For every failure, emit a JudgeIssue:
  - kind: "text_overlap" | "geometric_error" | "narration_mismatch"
          | "off_screen" | "wrong_object_count" | "duration_mismatch"
          | "color_legibility" | "other"
  - severity: "low" (cosmetic) | "medium" (should fix) | "high" (blocking)
  - where: which beat or frame range, e.g. "beat 2, around frame 4"
  - description: human-readable failure description
  - fix_hint: ACTIONABLE instruction a code-generating LLM can act on. Mention
    concrete Manim primitives (Polygon with vertices, VGroup.arrange, .next_to
    with explicit buff, .to_edge(DOWN), Transform vs TransformMatchingTex, etc.)
    and explicit numerical adjustments where relevant. NEVER write vague hints.

Set passed=True ONLY if there are zero high-severity and zero medium-severity
issues (low-severity cosmetic notes are tolerated).

Be strict on geometric correctness — that's the most common failure. If the
description says "rings unrolled into a triangle" and you see a parallelogram,
that is a HIGH severity geometric_error.

Output a JudgeReport JSON object. No prose, no fences.
"""


# ---------------------------------------------------------------------------
# Master QA
# ---------------------------------------------------------------------------

MASTER_QA_PROMPT = r"""You are the final QA reviewer for a multi-scene
explainer video. The user gives you:

  1. The full ScenePlan (all scenes).
  2. A list of per-scene results: rendered duration, attempts, success, last
     judge report.
  3. A deterministic pre-check report listing any obvious issues (duration
     drift > 40%, render failures, etc.).

Your job is to evaluate the OVERALL video — pacing, narrative arc, and
duration drift — and emit a structured QAReport.

For each problem, emit a QAIssue with:
  - scene_id: the scene's id ("01"...) or "global" for stitch-level concerns
  - kind: "duration_mismatch" | "narration_drift" | "render_error" |
          "visual_overlap" | "pacing" | "narrative_flow"
  - severity: low | medium | high
  - fix_hint: a concrete instruction that can be passed back to a scene worker
    as a `repair_brief` (e.g. "shorten beat 2 narration to one sentence to
    bring scene under 12 seconds").

Set overall_ok=True if there are no medium-or-high severity issues.

Be conservative — the per-scene Judge has already reviewed visuals. Your job
is mostly cross-scene flow and duration alignment, not individual scene bugs
unless they bubbled up from deterministic checks.

Output a QAReport JSON object. No prose, no fences.
"""
