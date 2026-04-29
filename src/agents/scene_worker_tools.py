"""Function-calling tools for the self-validating scene worker.

Defines the Gemini FunctionDeclaration schemas the worker exposes, plus
synchronous Python dispatchers that run when the model invokes a tool.

Per-attempt artifacts land at:
  output/<run_id>/<scene_id>/attempts/<NN>/
    scene.py                 # most recent code passed to render_manim
    scene.mp4                # rendered video (on success)
    log_tail.txt             # tail of manim stdout/stderr
    frames/frame_*.png       # extract_frames output

The worker keeps a WorkerToolContext that this module mutates as tools are
called (attempt counter, last render path, last code, etc.).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.agents.schemas import PriorContext
from src.agents.tools import (
    copy_to,
    extract_frames as _extract_frames_impl,
    probe_video,
    render_manim_scene,
)


# ---------------------------------------------------------------------------
# Function declarations exposed to the model
# ---------------------------------------------------------------------------

def get_function_declarations():
    """Return the list of types.FunctionDeclaration the worker exposes.

    Lazy import keeps the module loadable without google.genai installed.
    """
    from google.genai import types

    return [
        types.FunctionDeclaration(
            name="render_manim",
            description=(
                "Write the given Manim VoiceoverScene Python code to disk and "
                "run `manim` on it. Returns whether the render succeeded, the "
                "tail of manim's stdout/stderr, the path to the rendered mp4, "
                "and the measured duration in seconds. Call this every time "
                "you have a candidate scene file you want to validate. "
                "Each call uses a fresh attempt directory."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": (
                            "Complete Python source for one VoiceoverScene "
                            "subclass: imports, class definition, construct() body."
                        ),
                    },
                    "scene_class": {
                        "type": "string",
                        "description": (
                            "Class name to render. Must match the class defined "
                            "in `code` and the assigned scene_class for this scene."
                        ),
                    },
                },
                "required": ["code", "scene_class"],
            },
        ),
        types.FunctionDeclaration(
            name="extract_frames",
            description=(
                "Extract N evenly-spaced frames from a rendered video as PNGs. "
                "Call after render_manim succeeds to inspect what the scene "
                "actually looks like. Returns a list of {t_seconds, path}."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "video_path": {"type": "string"},
                    "n": {
                        "type": "integer",
                        "description": "Number of frames to extract (1-8). Default 4.",
                    },
                },
                "required": ["video_path"],
            },
        ),
        types.FunctionDeclaration(
            name="probe_audio",
            description=(
                "Inspect the audio track of a rendered video. Returns has_audio "
                "and duration_seconds. Use to verify the voiceover rendered."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "video_path": {"type": "string"},
                },
                "required": ["video_path"],
            },
        ),
        types.FunctionDeclaration(
            name="compare_to_prior_frame",
            description=(
                "Compare a frame from the current scene to the last frame of the "
                "prior scene (if any) and return a short text summary of "
                "continuity deltas — mobject geometry, color, label, position. "
                "Returns an empty diff when there is no prior scene. Use this "
                "to verify visual continuity across the cut before calling done."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "this_frame_path": {
                        "type": "string",
                        "description": (
                            "Path to a frame from the current scene. Use the FIRST "
                            "extracted frame to check the boundary with the prior scene."
                        ),
                    },
                },
                "required": ["this_frame_path"],
            },
        ),
        types.FunctionDeclaration(
            name="done",
            description=(
                "Declare the scene complete and stop the validation loop. "
                "REQUIRED to terminate. Pass video_path of the accepted render "
                "and a one-paragraph ending_state_summary describing exactly "
                "what is on screen at the END of this scene (camera, mobjects, "
                "their colors/positions, any persistent labels). The next "
                "scene's worker will read your summary to maintain continuity."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "video_path": {"type": "string"},
                    "ending_state_summary": {
                        "type": "string",
                        "description": (
                            "1-3 concrete sentences describing the final visible state. "
                            "Mention specific mobjects, colors, positions, labels."
                        ),
                    },
                },
                "required": ["video_path", "ending_state_summary"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Dispatch context + entrypoint
# ---------------------------------------------------------------------------

@dataclass
class WorkerToolContext:
    run_id: str
    scene_id: str
    project_root: Path
    artifacts_dir: Path           # output/<run_id>/<scene_id>/
    expected_class: str
    quality: str
    resolution: Optional[tuple[int, int]]
    prior_context: Optional[PriorContext]
    model: str
    attempt_idx: int = 0          # incremented by render_manim
    last_render_path: Optional[Path] = None
    last_code: Optional[str] = None
    last_log_tail: Optional[str] = None


def dispatch(name: str, args: dict, ctx: WorkerToolContext) -> dict:
    """Execute one tool call. Always returns a JSON-serializable dict.

    Never raises — errors are surfaced in the response payload so the model
    can recover and try a different approach.
    """
    try:
        if name == "render_manim":
            return _tool_render(args, ctx)
        if name == "extract_frames":
            return _tool_extract_frames(args, ctx)
        if name == "probe_audio":
            return _tool_probe_audio(args, ctx)
        if name == "compare_to_prior_frame":
            return _tool_compare(args, ctx)
        if name == "done":
            return _tool_done(args, ctx)
        return {"error": f"unknown tool {name!r}"}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------------------
# Individual tools
# ---------------------------------------------------------------------------

def _attempt_dir(ctx: WorkerToolContext, attempt: int) -> Path:
    p = ctx.artifacts_dir / "attempts" / f"{attempt:02d}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _tool_render(args: dict, ctx: WorkerToolContext) -> dict:
    code = str(args.get("code") or "")
    scene_class = str(args.get("scene_class") or "")
    if not code.strip():
        return {"success": False, "error": "code is empty"}

    # Pin the class name to the runner-assigned one so the mp4 lookup is stable.
    if scene_class != ctx.expected_class:
        code = _ensure_scene_class(code, ctx.expected_class)
    scene_class = ctx.expected_class

    ctx.attempt_idx += 1
    adir = _attempt_dir(ctx, ctx.attempt_idx)
    code_path = adir / "scene.py"
    code_path.write_text(code)
    ctx.last_code = code

    result = render_manim_scene(
        code_path, scene_class, ctx.quality,
        None, ctx.project_root, ctx.resolution,
    )

    log_tail = (result.log or "")[-2000:]
    (adir / "log_tail.txt").write_text(log_tail)
    ctx.last_log_tail = log_tail

    if not result.success or result.video_path is None:
        return {
            "success": False,
            "log_tail": log_tail,
            "video_path": None,
            "duration_s": None,
        }

    stable = adir / "scene.mp4"
    copy_to(result.video_path, stable)
    ctx.last_render_path = stable

    duration = probe_video(stable).duration
    return {
        "success": True,
        "log_tail": log_tail,
        "video_path": str(stable),
        "duration_s": round(duration, 3),
    }


def _tool_extract_frames(args: dict, ctx: WorkerToolContext) -> dict:
    video_path = _resolve_path(args.get("video_path"), ctx)
    n = int(args.get("n") or 4)
    n = max(1, min(n, 8))
    if not video_path or not video_path.exists():
        return {"error": f"video not found: {video_path}"}
    out_dir = video_path.parent / "frames"
    frames = _extract_frames_impl(video_path, n, out_dir)
    if not frames:
        return {"error": "no frames extracted"}
    duration = probe_video(video_path).duration
    timestamps = [(i + 0.5) * duration / len(frames) for i in range(len(frames))]
    return {
        "frames": [
            {"t_seconds": round(t, 3), "path": str(p)}
            for t, p in zip(timestamps, frames)
        ],
    }


def _tool_probe_audio(args: dict, ctx: WorkerToolContext) -> dict:
    video_path = _resolve_path(args.get("video_path"), ctx)
    if not video_path or not video_path.exists():
        return {"error": f"video not found: {video_path}"}
    info = probe_video(video_path)
    return {
        "has_audio": info.has_audio,
        "duration_s": round(info.duration, 3),
    }


def _tool_compare(args: dict, ctx: WorkerToolContext) -> dict:
    if ctx.prior_context is None or ctx.prior_context.last_frame_path is None:
        return {"diff_summary": "(no prior scene — this is the first scene)"}
    this_path = _resolve_path(args.get("this_frame_path"), ctx)
    if not this_path or not this_path.exists():
        return {"error": f"frame not found: {this_path}"}
    prior_path = Path(ctx.prior_context.last_frame_path)
    if not prior_path.exists():
        return {"error": f"prior frame missing: {prior_path}"}

    summary = _vision_diff(prior_path, this_path, ctx.model)
    return {"diff_summary": summary}


def _tool_done(args: dict, ctx: WorkerToolContext) -> dict:
    video_path = _resolve_path(args.get("video_path"), ctx)
    summary = str(args.get("ending_state_summary") or "").strip()
    if not summary:
        return {
            "accepted": False,
            "error": "ending_state_summary is required and must be non-empty.",
        }
    if not video_path or not video_path.exists():
        return {
            "accepted": False,
            "error": (
                f"video_path does not exist: {video_path}. "
                "Run render_manim successfully before calling done."
            ),
        }
    if video_path.stat().st_size < 1024:
        return {
            "accepted": False,
            "error": (
                f"video_path is suspiciously small ({video_path.stat().st_size} bytes). "
                "The render likely failed silently — re-run render_manim and inspect log_tail."
            ),
        }
    # Probe to verify the video is actually playable and has content. A
    # zero-duration mp4 means the manim run produced a header without frames;
    # missing audio means manim_voiceover failed to attach the narration.
    try:
        info = probe_video(video_path)
    except Exception as exc:
        return {
            "accepted": False,
            "error": (
                f"ffprobe could not read {video_path} ({exc!r}). "
                "Re-render the scene; the output is corrupt."
            ),
        }
    if info.duration < 0.5:
        return {
            "accepted": False,
            "error": (
                f"Video duration is {info.duration:.2f}s — too short to be a real scene. "
                "Re-render with the full beats list."
            ),
        }
    if not info.has_audio:
        return {
            "accepted": False,
            "error": (
                "Video has no audio track. The voiceover/TTS step did not run. "
                "Make sure construct() calls self.set_speech_service(GeminiTTSService(...)) "
                "and wraps each beat in `with self.voiceover(text=...) as tracker:`."
            ),
        }
    return {
        "accepted": True,
        "video_path": str(video_path),
        "ending_state_summary": summary,
        "duration_s": round(info.duration, 3),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_path(p, ctx: WorkerToolContext) -> Optional[Path]:
    if not p:
        return None
    path = Path(str(p))
    if not path.is_absolute():
        path = (ctx.project_root / path).resolve()
    return path


def _ensure_scene_class(code: str, expected: str) -> str:
    m = re.search(r"class\s+(\w+)\s*\(\s*VoiceoverScene\s*\)", code)
    if not m:
        return code
    actual = m.group(1)
    if actual == expected:
        return code
    return re.sub(rf"\b{re.escape(actual)}\b", expected, code)


def _vision_diff(prior_path: Path, this_path: Path, model: str) -> str:
    """Tiny Gemini vision call comparing two frames; returns a short prose diff."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return "(GOOGLE_API_KEY missing — continuity diff skipped)"

    client = genai.Client(api_key=api_key)
    contents = [
        types.Content(role="user", parts=[
            types.Part.from_bytes(data=prior_path.read_bytes(), mime_type="image/png"),
            types.Part.from_bytes(data=this_path.read_bytes(), mime_type="image/png"),
            types.Part.from_text(text=(
                "The first image is the LAST frame of the previous scene. "
                "The second image is the FIRST frame of the current scene. "
                "In 1-3 short sentences, describe whether the visual handoff is "
                "continuous: do persistent mobjects (shapes, axes, labels) keep "
                "their position, color, geometry, and orientation across the cut? "
                "Call out any drift you see; if continuity is good, say so. "
                "No preamble, no filler."
            )),
        ]),
    ]
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    return (response.text or "").strip() or "(no diff returned)"
