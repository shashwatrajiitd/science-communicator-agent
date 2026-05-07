"""Full-video reviewer for the tool-use scene worker.

Uploads a rendered scene mp4 via the Gemini Files API and asks Gemini 2.5
Pro to grade it on industry-mark criteria — animation timing, narration sync,
text readability, motion smoothness, mathematical correctness, continuity
with the prior scene. Returns a structured `VideoReviewReport` whose issues
each carry a timestamp range so the worker can locate and fix the specific
moment.

Two callers:
  - `scene_worker.render_scene_with_tools` runs this AFTER the model calls
    `done()`. If the report fails, the conversation is resumed with the
    formatted hints so the worker re-renders before the scene is accepted.
  - `plan_mode._interactive_scene_approval` runs this when the operator
    leaves a free-form comment. The reviewer translates the vague comment
    ("equation looks weird") into structured, code-anchored fix hints.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, Union

from src.agents.log import info, warn
from src.agents.schemas import ScenePlanItem, SubScene
from src.agents.tools import extract_frames, probe_video


PlanTarget = Union[ScenePlanItem, SubScene]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VideoReviewIssue:
    severity: str   # "low" | "medium" | "high" | "critical"
    kind: str       # "animation_timing", "narration_sync", "text_readability",
                    # "motion_quality", "color_palette", "math_correctness",
                    # "continuity", "composition", "pacing", "other"
    t_start_s: float
    t_end_s: float
    description: str
    fix_hint: str

    @staticmethod
    def from_dict(d: dict) -> "VideoReviewIssue":
        return VideoReviewIssue(
            severity=d.get("severity", "medium"),
            kind=d.get("kind", "other"),
            t_start_s=float(d.get("t_start_s", 0.0)),
            t_end_s=float(d.get("t_end_s", 0.0)),
            description=d.get("description", ""),
            fix_hint=d.get("fix_hint", ""),
        )


@dataclass
class VideoReviewReport:
    passed: bool
    overall_assessment: str
    issues: list[VideoReviewIssue] = field(default_factory=list)
    delivery: str = "video"   # "video" | "frames_fallback"

    @staticmethod
    def from_dict(d: dict) -> "VideoReviewReport":
        return VideoReviewReport(
            passed=bool(d.get("passed", False)),
            overall_assessment=d.get("overall_assessment", ""),
            issues=[VideoReviewIssue.from_dict(i) for i in d.get("issues", [])],
            delivery=d.get("delivery", "video"),
        )

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "overall_assessment": self.overall_assessment,
            "issues": [asdict(i) for i in self.issues],
            "delivery": self.delivery,
        }


# Gemini structured-output schema — mirrors VideoReviewReport.
_VIDEO_REVIEW_ISSUE_SCHEMA = {
    "type": "object",
    "properties": {
        "severity": {"type": "string"},
        "kind": {"type": "string"},
        "t_start_s": {"type": "number"},
        "t_end_s": {"type": "number"},
        "description": {"type": "string"},
        "fix_hint": {"type": "string"},
    },
    "required": ["severity", "kind", "t_start_s", "t_end_s",
                 "description", "fix_hint"],
}

VIDEO_REVIEW_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "passed": {"type": "boolean"},
        "overall_assessment": {"type": "string"},
        "issues": {"type": "array", "items": _VIDEO_REVIEW_ISSUE_SCHEMA},
    },
    "required": ["passed", "overall_assessment", "issues"],
}


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

# Files API processing-poll budget. Most short scenes go ACTIVE in 2-5s; we
# allow up to 60s for longer videos before giving up and falling back.
_PROCESSING_POLL_SECONDS = 60
_PROCESSING_POLL_INTERVAL = 2.0


def review_scene_video(
    video_path: Path,
    target: PlanTarget,
    plan,
    *,
    prior_last_frame: Optional[Path] = None,
    user_comment: Optional[str] = None,
    prior_code: Optional[str] = None,
    model: str = "gemini-2.5-pro",
    fallback_to_frames: bool = True,
    parent_scene_id: Optional[str] = None,
) -> VideoReviewReport:
    """Run the reviewer against a rendered scene.

    On Files-API failure (upload timeout / processing failed / generate
    error), if `fallback_to_frames` is True, the same prompt is rerun with
    8 extracted PNG frames instead of the video URI. The returned report's
    `delivery` field records which path was used.

    Synchronous; intended to be wrapped in `asyncio.to_thread` by callers.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        return VideoReviewReport(
            passed=False,
            overall_assessment=f"Video not found at {video_path}",
            issues=[],
            delivery="video",
        )

    duration = 0.0
    try:
        duration = probe_video(video_path).duration
    except Exception:
        pass

    prompt = _review_prompt(target, plan, duration,
                            prior_last_frame=prior_last_frame,
                            user_comment=user_comment,
                            prior_code=prior_code,
                            parent_scene_id=parent_scene_id)

    scope = _scope_for(target, parent_scene_id)
    info(scope, f"video review starting — model={model} duration={duration:.1f}s "
                f"comment={'yes' if user_comment else 'no'}")

    # First try: upload video via Files API.
    try:
        report = _review_via_video_upload(video_path, prompt, prior_last_frame, model)
        report.delivery = "video"
        info(scope, f"video review done — passed={report.passed} issues={len(report.issues)}")
        return report
    except Exception as exc:
        warn(scope, f"video upload review failed ({type(exc).__name__}: {exc}); "
                    f"fallback_to_frames={fallback_to_frames}")
        if not fallback_to_frames:
            return VideoReviewReport(
                passed=False,
                overall_assessment=f"Reviewer error (upload path): {exc}",
                issues=[],
                delivery="video",
            )

    # Fallback: extract frames and rerun the same prompt.
    try:
        report = _review_via_frames(video_path, prompt, prior_last_frame, model)
        report.delivery = "frames_fallback"
        info(scope, f"frames-fallback review done — passed={report.passed} "
                    f"issues={len(report.issues)}")
        return report
    except Exception as exc:
        warn(scope, f"frames-fallback review failed ({type(exc).__name__}: {exc})")
        return VideoReviewReport(
            passed=False,
            overall_assessment=f"Reviewer error (both paths): {exc}",
            issues=[],
            delivery="frames_fallback",
        )


# ---------------------------------------------------------------------------
# Delivery: upload + Gemini call
# ---------------------------------------------------------------------------

def _review_via_video_upload(video_path: Path, prompt: str,
                             prior_last_frame: Optional[Path],
                             model: str) -> VideoReviewReport:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in env.")

    client = genai.Client(api_key=api_key)

    uploaded = client.files.upload(file=str(video_path))
    try:
        # Poll until ACTIVE.
        deadline = time.monotonic() + _PROCESSING_POLL_SECONDS
        while True:
            state = getattr(uploaded.state, "name", str(uploaded.state))
            if state == "ACTIVE":
                break
            if state == "FAILED":
                raise RuntimeError(
                    f"Files API processing failed: {getattr(uploaded, 'error', '')}"
                )
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Files API stuck in {state} after {_PROCESSING_POLL_SECONDS}s"
                )
            time.sleep(_PROCESSING_POLL_INTERVAL)
            uploaded = client.files.get(name=uploaded.name)

        parts: list = [types.Part.from_uri(
            file_uri=uploaded.uri,
            mime_type=uploaded.mime_type or "video/mp4",
        )]
        if prior_last_frame is not None and Path(prior_last_frame).exists():
            try:
                parts.append(types.Part.from_bytes(
                    data=Path(prior_last_frame).read_bytes(),
                    mime_type="image/png",
                ))
            except OSError:
                pass
        parts.append(types.Part.from_text(text=prompt))

        response = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                media_resolution="MEDIA_RESOLUTION_LOW",
                response_mime_type="application/json",
                response_schema=VIDEO_REVIEW_REPORT_SCHEMA,
                temperature=0.2,
                system_instruction=_REVIEWER_SYSTEM_PROMPT,
            ),
        )
        return _parse_response(response)
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass


def _review_via_frames(video_path: Path, prompt: str,
                       prior_last_frame: Optional[Path],
                       model: str) -> VideoReviewReport:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in env.")

    frames_dir = video_path.parent / f"{video_path.stem}_review_frames"
    frames = extract_frames(video_path, 8, frames_dir)
    if not frames:
        raise RuntimeError("could not extract any frames for fallback review")

    parts: list = []
    if prior_last_frame is not None and Path(prior_last_frame).exists():
        try:
            parts.append(types.Part.from_bytes(
                data=Path(prior_last_frame).read_bytes(),
                mime_type="image/png",
            ))
        except OSError:
            pass
    for f in frames:
        parts.append(types.Part.from_bytes(
            data=Path(f).read_bytes(),
            mime_type="image/png",
        ))
    # When using frames the model can't see motion — tell it explicitly.
    framed_prompt = (
        prompt
        + "\n\nNOTE: The video upload path failed; the frames above were "
        "extracted at evenly-spaced timestamps from the rendered scene. "
        "Estimate timestamps by frame position (1st frame ≈ 0s, last frame "
        "≈ duration). You cannot judge motion smoothness directly — focus "
        "on what's visible in the frames."
    )
    parts.append(types.Part.from_text(text=framed_prompt))

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VIDEO_REVIEW_REPORT_SCHEMA,
            temperature=0.2,
            system_instruction=_REVIEWER_SYSTEM_PROMPT,
        ),
    )
    return _parse_response(response)


def _parse_response(response) -> VideoReviewReport:
    text = getattr(response, "text", None) or "{}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return VideoReviewReport(
            passed=False,
            overall_assessment=f"Reviewer returned invalid JSON: {text[:300]}",
            issues=[],
            delivery="video",
        )
    return VideoReviewReport.from_dict(data)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_REVIEWER_SYSTEM_PROMPT = """\
You are a senior animation reviewer for a 3Blue1Brown-style explainer
channel. You inspect a rendered Manim scene and decide whether it meets
industry quality bar.

Apply these criteria, in priority order:

1. **Mathematical / factual correctness** — equations, labels, geometric
   relationships, axis scales must be right. A wrong sign or mis-rendered
   exponent is `critical` even if the animation looks pretty.
2. **Narration ↔ visual sync** — the voiceover and on-screen events must
   line up. If the line "as the wave morphs into a circle" finishes 1.5s
   before the wave starts morphing, that's `high` `narration_sync`.
3. **Animation timing & motion quality** — no jerky/instant transitions
   that should be smooth, no slow drags that should snap. No mobjects
   appearing/disappearing without an easing transition.
4. **Text readability** — labels readable at 1080p; no clipping at frame
   edges; font weight legible against the background.
5. **Continuity with prior scene** — when a previous-scene last frame is
   provided, persistent mobjects must keep their position, color,
   geometry across the cut. A jump cut on a shared object is `high`.
6. **Composition & color palette** — 3Blue1Brown aesthetic: dark navy
   background, restrained palette, comfortable margins, primary mobject
   centered or rule-of-thirds. Cluttered, oversaturated, or off-palette
   compositions are `medium`.
7. **Pacing per beat** — each narrated beat should have a corresponding
   visual moment; long stretches of static video while narration runs
   are `medium` `pacing`.

For EVERY issue you flag, return a `t_start_s`/`t_end_s` range pinpointing
when in the video the issue occurs. Be conservative: if you're not sure,
err on a wider window so the worker can find it.

`fix_hint` must be CONCRETE and actionable in Manim code. Prefer
"shorten the Write(eq) run_time from 2.0 to 1.0" over "speed up the
equation". When previous code is provided, reference symbol names.

Set `passed=true` only when there are no `high` or `critical` issues AND
the overall scene meets the industry bar. Otherwise `passed=false`.

You may surface 0 issues with `passed=true` (the scene is clean) or
include `low`-severity polish notes alongside `passed=true` (acceptable
but room to improve).

Return JSON matching the VideoReviewReport schema. No prose outside JSON.
"""


def _review_prompt(target: PlanTarget, plan, measured_duration: float,
                   *, prior_last_frame: Optional[Path] = None,
                   user_comment: Optional[str] = None,
                   prior_code: Optional[str] = None,
                   parent_scene_id: Optional[str] = None) -> str:
    target_seconds = target.target_seconds
    beats = target.beats or []
    beats_text = "\n".join(
        f"  Beat {i+1}: text={b.text!r}\n         hint={b.animation_hint!r}"
        for i, b in enumerate(beats)
    )
    checks = "\n".join(f"  - {c}" for c in (target.correctness_checks or []))
    visuals = "\n".join(f"  - {v}" for v in (target.key_visuals or []))

    shared_block = ""
    if plan is not None and hasattr(plan, "shared_objects_for_scene"):
        scene_id = parent_scene_id or getattr(target, "id", "")
        shared = plan.shared_objects_for_scene(scene_id)
        if shared:
            shared_lines = []
            for o in shared:
                label = f' label="{o.label}"' if o.label else ""
                shared_lines.append(
                    f"  - name: {o.name}\n"
                    f"    color: {o.color}{label}\n"
                    f"    spec: {o.spec}"
                )
            shared_block = (
                "\n\nshared_objects (these MUST be drawn EXACTLY per spec; a "
                "mismatched shape, orientation, or color is a high severity "
                "continuity issue):\n" + "\n".join(shared_lines)
            )

    prior_block = ""
    if prior_last_frame is not None and Path(prior_last_frame).exists():
        prior_block = (
            "\n\nThe IMAGE attached BEFORE the video is the LAST frame of "
            "the previous scene. Use it to judge continuity at the cut: "
            "persistent mobjects (shapes, axes, labels) should keep their "
            "position, color, geometry across the boundary."
        )

    comment_block = ""
    if user_comment:
        comment_block = (
            "\n\n# OPERATOR COMMENT — anchor your review on this\n"
            "The human reviewer left this free-form comment on the scene:\n"
            f"  > {user_comment.strip()}\n"
            "Translate the comment into structured issues with concrete "
            "timestamps and code-actionable fix_hints. You MAY also surface "
            "any other high-severity issues you spot, but the comment is "
            "the priority — make sure it produces at least one issue."
        )

    code_block = ""
    if prior_code:
        # Truncate giant scripts so we don't blow the prompt budget.
        snippet = prior_code if len(prior_code) <= 8000 else prior_code[:8000] + "\n# … (truncated)"
        code_block = (
            "\n\n# PREVIOUS SCENE CODE (the worker rendered this)\n"
            "Reference symbol names from the code in your fix_hints — say "
            "`shorten Write(eq) run_time` not `speed up the equation`.\n"
            "```python\n" + snippet + "\n```"
        )

    return f"""SCENE TO REVIEW
description: {target.description}
target_duration: {target_seconds:.1f} seconds
measured_duration: {measured_duration:.1f} seconds

key_visuals:
{visuals or '  (none)'}

correctness_checks (acceptance criteria):
{checks or '  (none)'}

planned narration beats (verbatim):
{beats_text or '  (no narration)'}{shared_block}{prior_block}{comment_block}{code_block}

The video above is the rendered scene. Watch it end-to-end. Apply the
industry-bar criteria from the system prompt. Return a VideoReviewReport
JSON object."""


# ---------------------------------------------------------------------------
# Hint formatting + thrashing detection
# ---------------------------------------------------------------------------

def format_video_review_hints(report: VideoReviewReport) -> str:
    """Render the report into a fix-brief for the worker.

    Mirrors `format_judge_hints` in judge.py but adds timestamp ranges so
    the worker can locate each issue precisely. Severity-sorted so the
    most impactful fixes appear first.
    """
    if not report.issues:
        if report.passed:
            return f"REVIEWER OK: {report.overall_assessment or '(no issues)'}"
        return f"REVIEWER FAILED but reported no specific issues: {report.overall_assessment}"

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_issues = sorted(
        report.issues,
        key=lambda i: severity_rank.get(i.severity, 9),
    )

    lines = ["REVIEWER FEEDBACK — fix the following before calling done() again:"]
    for i, issue in enumerate(sorted_issues, 1):
        t = f"{issue.t_start_s:.1f}s–{issue.t_end_s:.1f}s"
        lines.append(
            f"\n[{i}] [{issue.severity}] {issue.kind} at {t}"
            f"\n  problem: {issue.description}"
            f"\n  fix:     {issue.fix_hint}"
        )
    if report.overall_assessment:
        lines.append(f"\nOverall: {report.overall_assessment}")
    lines.append(
        "\nGenerate corrected code with render_manim, validate, then call "
        "done() again. The reviewer will run again on the new render."
    )
    return "\n".join(lines)


def no_progress(prev: VideoReviewReport, curr: VideoReviewReport) -> bool:
    """Return True when the model is thrashing: no high-severity issue from
    the previous round has been resolved in the current round AND the
    overall issue count hasn't dropped.

    Conservative: returns False if either side has no issues (not enough
    signal to call thrashing).
    """
    if not prev.issues or not curr.issues:
        return False
    prev_high = {(i.severity, i.kind) for i in prev.issues
                 if i.severity in ("high", "critical")}
    curr_high = {(i.severity, i.kind) for i in curr.issues
                 if i.severity in ("high", "critical")}
    if not prev_high:
        return False
    # No prior high-severity (kind) is GONE in current AND issue count
    # didn't drop.
    if prev_high.issubset(curr_high) and len(curr.issues) >= len(prev.issues):
        return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scope_for(target: PlanTarget, parent_scene_id: Optional[str]) -> str:
    if isinstance(target, SubScene):
        return f"reviewer:{parent_scene_id}__{target.id}" if parent_scene_id else f"reviewer:{target.id}"
    return f"reviewer:{getattr(target, 'id', '?')}"
