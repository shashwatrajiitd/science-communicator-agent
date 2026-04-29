"""Vision-based per-scene judge.

Uses Gemini 2.5 Pro multimodal: feeds N sampled frames + the planned beats
+ the scene description and correctness checks. Returns a structured
JudgeReport that gates whether a scene is acceptable.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv

from src.agents.prompts import JUDGE_PROMPT
from src.agents.schemas import (
    JUDGE_REPORT_SCHEMA,
    JudgeReport,
    ScenePlanItem,
    SubScene,
)
from src.agents.tools import extract_frames, probe_video

load_dotenv()


PlanTarget = Union[ScenePlanItem, SubScene]


def _client():
    from google import genai
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in .env.")
    return genai.Client(api_key=api_key)


async def judge_scene(
    target: PlanTarget,
    video_path: Path,
    *,
    frames_dir: Path,
    n_frames: int = 8,
    model: str = "gemini-2.5-pro",
    continuity_mode: bool = False,
    plan: Optional[object] = None,
    parent_scene_id: Optional[str] = None,
) -> JudgeReport:
    """Run the visual + narration judge against `video_path`.

    `target` is the scene or sub-scene being judged. `continuity_mode=True` is
    used after concatenating sub-scenes to focus on narrative flow.

    If `plan` is provided, the judge is told about any `shared_objects`
    relevant to this scene (looked up via `parent_scene_id` for sub-scenes,
    or `target.id` for top-level scenes).
    """
    video_path = Path(video_path)
    frames_dir = Path(frames_dir)

    info = probe_video(video_path)
    frames = extract_frames(video_path, n_frames, frames_dir)
    if not frames:
        return JudgeReport(
            passed=False,
            overall_assessment="Could not extract any frames for review.",
            issues=[],
        )

    shared_for_scene = []
    if plan is not None and hasattr(plan, "shared_objects_for_scene"):
        scene_id = parent_scene_id or getattr(target, "id", "")
        shared_for_scene = plan.shared_objects_for_scene(scene_id)

    user_msg = _build_user_text(target, info.duration, continuity_mode, shared_for_scene)

    json_text = await asyncio.to_thread(
        _call_judge, model, user_msg, frames
    )
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        # If structured output fails, fail closed (mark as not passed).
        return JudgeReport(
            passed=False,
            overall_assessment=f"Judge returned invalid JSON: {json_text[:300]}",
            issues=[],
        )
    return JudgeReport.from_dict(data)


def _build_user_text(target: PlanTarget, measured_duration: float,
                     continuity_mode: bool,
                     shared_objects: Optional[list] = None) -> str:
    target_seconds = target.target_seconds
    beats = target.beats or []
    beats_text = "\n".join(
        f"  Beat {i+1}: text={b.text!r}\n         hint={b.animation_hint!r}"
        for i, b in enumerate(beats)
    )
    checks = "\n".join(f"  - {c}" for c in (target.correctness_checks or []))
    visuals = "\n".join(f"  - {v}" for v in (target.key_visuals or []))

    shared_block = ""
    if shared_objects:
        shared_lines = []
        for o in shared_objects:
            label = f' label="{o.label}"' if o.label else ""
            shared_lines.append(
                f"  - name: {o.name}\n"
                f"    color: {o.color}{label}\n"
                f"    spec: {o.spec}"
            )
        shared_block = (
            "\n\nshared_objects (these MUST be drawn EXACTLY per spec for cross-scene\n"
            "continuity. A mismatched shape/orientation is a HIGH severity\n"
            "geometric_error even if the shape is correct in isolation):\n"
            + "\n".join(shared_lines)
        )

    mode_note = ""
    if continuity_mode:
        mode_note = (
            "\n\nNOTE: This is a CONTINUITY pass on a concatenated multi-segment "
            "scene. Focus on whether the cuts feel coherent and the sub-segments "
            "tell one continuous story. Per-segment issues should already have "
            "been caught."
        )

    return f"""SCENE TO JUDGE
description: {target.description}
target_duration: {target_seconds:.1f} seconds
measured_duration: {measured_duration:.1f} seconds

key_visuals:
{visuals or '  (none)'}

correctness_checks (acceptance criteria):
{checks or '  (none)'}

planned narration beats (verbatim):
{beats_text or '  (no narration)'}{shared_block}{mode_note}

The N frames below are sampled in chronological order. Inspect them against
the description, the correctness_checks, the shared_objects, and the
narration. Decide whether the scene passes. Output a JudgeReport JSON object."""


def _call_judge(model: str, user_msg: str, frame_paths: list[Path]) -> str:
    from google.genai import types

    parts: list = []
    for p in frame_paths:
        parts.append(
            types.Part.from_bytes(data=p.read_bytes(), mime_type="image/png")
        )
    parts.append(types.Part.from_text(text=user_msg))
    contents = [types.Content(role="user", parts=parts)]

    client = _client()
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=JUDGE_PROMPT,
            response_mime_type="application/json",
            response_schema=JUDGE_REPORT_SCHEMA,
            temperature=0.2,
        ),
    )
    return response.text or "{}"


def format_judge_hints(report: JudgeReport) -> str:
    """Render a JudgeReport into a fix-brief for the worker's repair_scene."""
    if not report.issues:
        return report.overall_assessment or "(no specific issues)"
    lines = ["VISUAL/AUDIO JUDGE FAILED — fix the following issues:"]
    for i, issue in enumerate(report.issues, 1):
        lines.append(
            f"\n[{i}] severity={issue.severity}  kind={issue.kind}  where={issue.where}"
            f"\n  problem: {issue.description}"
            f"\n  fix:     {issue.fix_hint}"
        )
    if report.overall_assessment:
        lines.append(f"\nOverall: {report.overall_assessment}")
    return "\n".join(lines)
