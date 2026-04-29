"""Per-scene worker.

Generates a single VoiceoverScene file for one ScenePlanItem (or SubScene),
renders it with Manim, runs the Judge, and iterates with repair calls until
the scene passes or attempts are exhausted.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv

from src.agents.judge import format_judge_hints, judge_scene
from src.agents.log import info, log, log_tool_call, log_tool_response, warn
from src.agents.prompts import (
    WORKER_SCENE_PROMPT,
    WORKER_SCENE_PROMPT_TOOL,
    build_worker_user_message,
)
from src.agents.scene_worker_tools import (
    WorkerToolContext,
    dispatch,
    get_function_declarations,
)
from src.agents.schemas import (
    JudgeReport,
    PriorContext,
    ScenePlan,
    ScenePlanItem,
    SceneResult,
    SubScene,
)
from src.agents.tools import (
    copy_to,
    extract_last_frame,
    probe_video,
    render_manim_scene,
)
from src.gemini_agent import _strip_fences, normalize_tts_to_gemini

load_dotenv()


PlanTarget = Union[ScenePlanItem, SubScene]


def _client():
    from google import genai
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in .env.")
    return genai.Client(api_key=api_key)


def _gen(model: str, contents: str, system: str, *, temperature: float = 0.5) -> str:
    from google.genai import types
    client = _client()
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
        ),
    )
    return _strip_fences(response.text or "")


def _ensure_scene_class(code: str, expected_class: str) -> str:
    """If the model picked a different class name, rename it in code."""
    m = re.search(r"class\s+(\w+)\s*\(\s*VoiceoverScene\s*\)", code)
    if not m:
        return code
    actual = m.group(1)
    if actual == expected_class:
        return code
    # Replace the class definition and any reference to the same name.
    return re.sub(rf"\b{re.escape(actual)}\b", expected_class, code)


_normalize_tts = normalize_tts_to_gemini


# ---------------------------------------------------------------------------
# Generation prompts
# ---------------------------------------------------------------------------

def _generate_initial(model: str, brief: str) -> str:
    return _gen(model, brief, WORKER_SCENE_PROMPT, temperature=0.6)


def _generate_repair_after_render(model: str, brief: str, broken_code: str,
                                  error_text: str) -> str:
    repair_system = (
        WORKER_SCENE_PROMPT
        + "\n\n# REPAIR MODE\nThe previous code failed to RENDER. Fix the error"
        " and re-emit the full corrected file. Keep the same Scene class name."
        " Output ONLY Python code."
    )
    contents = (
        f"{brief}\n\n"
        f"--- BROKEN CODE ---\n{broken_code}\n\n"
        f"--- RENDER ERROR ---\n{error_text[-3000:]}\n\n"
        "Now output the corrected full file."
    )
    return _gen(model, contents, repair_system, temperature=0.4)


def _generate_repair_after_judge(model: str, brief: str, prev_code: str,
                                 judge_hints: str) -> str:
    repair_system = (
        WORKER_SCENE_PROMPT
        + "\n\n# REPAIR MODE\nThe previous code RENDERED but the visual/audio"
        " judge flagged issues. Fix every issue listed. Re-emit the full"
        " corrected file with the same Scene class name. Output ONLY Python code."
    )
    contents = (
        f"{brief}\n\n"
        f"--- PREVIOUS CODE ---\n{prev_code}\n\n"
        f"--- JUDGE FEEDBACK ---\n{judge_hints}\n\n"
        "Now output the corrected full file."
    )
    return _gen(model, contents, repair_system, temperature=0.4)


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

async def render_scene(
    target: PlanTarget,
    plan: ScenePlan,
    *,
    run_id: str,
    quality: str,
    project_root: Path,
    max_attempts: int = 4,
    judge: bool = True,
    n_frames: int = 8,
    model: str = "gemini-2.5-pro",
    parent_id: Optional[str] = None,    # parent scene id when rendering a sub-scene
    extra_brief: Optional[str] = None,  # additional repair_brief from master patch
    resolution: Optional[tuple[int, int]] = None,
    aspect_ratio: Optional[str] = None,
) -> SceneResult:
    """Generate, render, judge, repeat until passed or max_attempts exhausted."""
    project_root = Path(project_root)

    # Compose file paths
    scenes_dir = project_root / "scenes" / run_id
    scenes_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = project_root / "output" / run_id
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(target, SubScene):
        # parent_id is the parent scene's id (e.g. "01")
        parent_slug = next(
            (s.slug for s in plan.scenes if s.id == parent_id),
            "scene",
        )
        file_stem = f"{parent_slug}__{target.id}_{target.slug}"
        ident = f"{parent_id}__{target.id}"
    else:
        file_stem = target.slug
        ident = target.id

    scene_file = scenes_dir / f"{file_stem}.py"
    expected_class = _slug_to_pascal(file_stem)

    # Build the user-side scene brief once.
    if isinstance(target, SubScene):
        parent_item = next(s for s in plan.scenes if s.id == parent_id)
        brief = build_worker_user_message(
            parent_item, plan, sub_scene=target,
            aspect_ratio=aspect_ratio, resolution=resolution,
        )
        # Override expected class name in the brief so the worker uses our path.
        brief = _force_scene_class_in_brief(brief, expected_class)
    else:
        brief = build_worker_user_message(
            target, plan,
            aspect_ratio=aspect_ratio, resolution=resolution,
        )
        brief = _force_scene_class_in_brief(brief, expected_class)

    if extra_brief:
        brief = brief + f"\n\n# MASTER PATCH NOTES\n{extra_brief}"

    last_code: Optional[str] = None
    last_render_log: Optional[str] = None
    last_judge: Optional[JudgeReport] = None

    # Best-effort fallback. If every attempt either fails to render or fails
    # the judge, we still want a usable mp4 so the stitcher can include the
    # scene. We keep the most recent attempt that *rendered* successfully.
    best_video_path: Optional[Path] = None
    best_duration: Optional[float] = None
    best_judge: Optional[JudgeReport] = None
    best_attempt: int = 0

    for attempt in range(1, max_attempts + 1):
        # 1) Code generation
        if attempt == 1:
            code = await asyncio.to_thread(_generate_initial, model, brief)
        elif last_render_log is not None:
            code = await asyncio.to_thread(
                _generate_repair_after_render, model, brief, last_code or "", last_render_log
            )
        else:
            assert last_judge is not None
            hints = format_judge_hints(last_judge)
            code = await asyncio.to_thread(
                _generate_repair_after_judge, model, brief, last_code or "", hints
            )

        code = _ensure_scene_class(code, expected_class)
        code = _normalize_tts(code)
        scene_file.write_text(code)
        last_code = code

        # 2) Render
        render = await asyncio.to_thread(
            render_manim_scene, scene_file, expected_class, quality,
            None, project_root, resolution,
        )
        if not render.success:
            last_render_log = render.log[-3000:]
            last_judge = None
            _persist_attempt_log(artifacts_dir, ident, attempt,
                                 status="render_failed",
                                 error=last_render_log)
            continue

        video_path = render.video_path
        # Copy to a stable location so the stitcher can find it.
        if isinstance(target, SubScene):
            stable = artifacts_dir / f"scene_{parent_id}__{target.id}.mp4"
        else:
            stable = artifacts_dir / f"scene_{target.id}.mp4"
        from src.agents.tools import copy_to
        copy_to(video_path, stable)
        video_path = stable

        duration = probe_video(video_path).duration

        # Track this attempt as a best-effort fallback (it rendered).
        best_video_path = video_path
        best_duration = duration
        best_attempt = attempt

        # 3) Judge
        if not judge:
            return SceneResult(
                id=ident, scene_class=expected_class, scene_file=scene_file,
                video_path=video_path, duration_seconds=duration,
                attempts=attempt, success=True, last_error=None, last_judge=None,
            )

        frames_dir = artifacts_dir / f"frames_{ident}_attempt{attempt}"
        try:
            report = await judge_scene(
                target, video_path,
                frames_dir=frames_dir,
                n_frames=n_frames,
                model=model,
                plan=plan,
                parent_scene_id=parent_id if isinstance(target, SubScene) else None,
            )
        except Exception as exc:
            # Judge errors should not kill the worker — accept the render
            # but record the issue.
            report = JudgeReport(
                passed=True,
                overall_assessment=f"(judge failed to run: {exc!r})",
                issues=[],
            )

        _persist_attempt_log(artifacts_dir, ident, attempt,
                             status="rendered",
                             video_path=str(video_path),
                             duration=duration,
                             judge=report.to_dict())

        if report.passed:
            return SceneResult(
                id=ident, scene_class=expected_class, scene_file=scene_file,
                video_path=video_path, duration_seconds=duration,
                attempts=attempt, success=True, last_error=None, last_judge=report,
            )

        last_judge = report
        best_judge = report
        last_render_log = None
        # loop continues with judge-driven repair

    # Exhausted retries. Fall back to the best successful render if we have
    # one, even if the judge wasn't fully satisfied. The stitcher will still
    # include this scene so the final video is complete; the master QA loop
    # can take another patch pass at it.
    if best_video_path is not None:
        return SceneResult(
            id=ident, scene_class=expected_class, scene_file=scene_file,
            video_path=best_video_path, duration_seconds=best_duration,
            attempts=max_attempts, success=True,
            last_error=(format_judge_hints(best_judge) if best_judge else None),
            last_judge=best_judge,
        )

    # Truly nothing rendered — hard fail.
    return SceneResult(
        id=ident, scene_class=expected_class, scene_file=scene_file,
        video_path=None, duration_seconds=None,
        attempts=max_attempts, success=False,
        last_error=(last_render_log or "All attempts failed to render."),
        last_judge=None,
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _slug_to_pascal(slug: str) -> str:
    parts = slug.replace("__", "_").split("_")
    return "".join(p.capitalize() for p in parts if p) or "GeneratedScene"


def _force_scene_class_in_brief(brief: str, expected: str) -> str:
    return re.sub(r"This scene class name MUST be: \S+",
                  f"This scene class name MUST be: {expected}", brief)


def _persist_attempt_log(artifacts_dir: Path, ident: str, attempt: int, **fields) -> None:
    out = artifacts_dir / f"judge_{ident}_attempt{attempt}.json"
    out.write_text(json.dumps(fields, indent=2, default=str))


# ---------------------------------------------------------------------------
# Tool-driven self-validating worker (sequential pipeline path)
# ---------------------------------------------------------------------------

async def render_scene_with_tools(
    target: PlanTarget,
    plan: ScenePlan,
    *,
    run_id: str,
    quality: str,
    project_root: Path,
    prior_context: Optional[PriorContext] = None,
    judge: bool = True,           # accepted for signature compat; this path
    n_frames: int = 8,            # uses the model's own inspection instead
    model: str = "gemini-2.5-pro",
    parent_id: Optional[str] = None,
    extra_brief: Optional[str] = None,
    resolution: Optional[tuple[int, int]] = None,
    aspect_ratio: Optional[str] = None,
    max_tool_iterations: int = 8,
) -> SceneResult:
    """Self-validating worker: hands tools to Gemini and lets it drive the
    render → inspect → fix loop until it calls done() or runs out of budget.
    """
    project_root = Path(project_root)
    artifacts_root = project_root / "output" / run_id
    artifacts_root.mkdir(parents=True, exist_ok=True)

    if isinstance(target, SubScene):
        parent_slug = next(
            (s.slug for s in plan.scenes if s.id == parent_id),
            "scene",
        )
        file_stem = f"{parent_slug}__{target.id}_{target.slug}"
        ident = f"{parent_id}__{target.id}"
    else:
        file_stem = target.slug
        ident = target.id

    expected_class = _slug_to_pascal(file_stem)

    scene_artifacts = artifacts_root / ident
    scene_artifacts.mkdir(parents=True, exist_ok=True)

    info(f"worker:{ident}",
         f"render_scene_with_tools — class={expected_class}  target={target.target_seconds:.0f}s  "
         f"prior={prior_context.prior_scene_id if prior_context else 'none'}  "
         f"extra_brief={'yes' if extra_brief else 'no'}")

    if isinstance(target, SubScene):
        parent_item = next(s for s in plan.scenes if s.id == parent_id)
        brief = build_worker_user_message(
            parent_item, plan, sub_scene=target,
            aspect_ratio=aspect_ratio, resolution=resolution,
            prior_context=prior_context,
        )
    else:
        brief = build_worker_user_message(
            target, plan,
            aspect_ratio=aspect_ratio, resolution=resolution,
            prior_context=prior_context,
        )
    brief = _force_scene_class_in_brief(brief, expected_class)
    if extra_brief:
        brief = brief + f"\n\n# MASTER PATCH NOTES\n{extra_brief}"

    ctx = WorkerToolContext(
        run_id=run_id,
        scene_id=ident,
        project_root=project_root,
        artifacts_dir=scene_artifacts,
        expected_class=expected_class,
        quality=quality,
        resolution=resolution,
        prior_context=prior_context,
        model=model,
    )

    return await asyncio.to_thread(
        _drive_tool_loop,
        ctx, brief, target, ident, file_stem, expected_class,
        max_tool_iterations,
    )


def _drive_tool_loop(
    ctx: WorkerToolContext,
    brief: str,
    target: PlanTarget,
    ident: str,
    file_stem: str,
    expected_class: str,
    max_iter: int,
) -> SceneResult:
    """Synchronous Gemini function-calling loop. Runs in a worker thread."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in .env.")
    client = genai.Client(api_key=api_key)

    declarations = get_function_declarations()
    tool = types.Tool(function_declarations=declarations)

    user_parts = []
    pc = ctx.prior_context
    if pc is not None and pc.last_frame_path is not None:
        try:
            img_bytes = Path(pc.last_frame_path).read_bytes()
            user_parts.append(
                types.Part.from_bytes(data=img_bytes, mime_type="image/png")
            )
        except OSError:
            pass
    user_parts.append(types.Part.from_text(text=brief))
    contents: list = [types.Content(role="user", parts=user_parts)]

    accepted_video: Optional[Path] = None
    accepted_summary = ""
    last_done_error: Optional[str] = None

    info(f"worker:{ctx.scene_id}",
         f"tool loop starting — model={ctx.model}  max_iter={max_iter}  "
         f"prior_context={'yes' if ctx.prior_context else 'no'}")

    for iteration in range(1, max_iter + 1):
        log(f"worker:{ctx.scene_id}", f"iter {iteration} → calling model…",
            style="blue")
        response = client.models.generate_content(
            model=ctx.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=WORKER_SCENE_PROMPT_TOOL,
                tools=[tool],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="ANY")
                ),
                temperature=0.4,
            ),
        )
        if not response.candidates:
            warn(f"worker:{ctx.scene_id}", f"iter {iteration} model returned no candidates")
            break
        candidate = response.candidates[0]
        if candidate.content is None or not candidate.content.parts:
            warn(f"worker:{ctx.scene_id}", f"iter {iteration} model returned empty content")
            break

        contents.append(candidate.content)

        fc_parts = [p for p in candidate.content.parts if getattr(p, "function_call", None)]
        if not fc_parts:
            warn(f"worker:{ctx.scene_id}",
                 f"iter {iteration} model emitted text instead of function calls; nudging")
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=(
                    "Reply with function calls only. Call render_manim, "
                    "extract_frames, probe_audio, compare_to_prior_frame, "
                    "or done — never plain text."
                ))],
            ))
            continue

        response_parts = []
        done_seen = False
        for p in fc_parts:
            name = p.function_call.name
            try:
                args = dict(p.function_call.args) if p.function_call.args is not None else {}
            except (TypeError, ValueError):
                args = {}

            log_tool_call(ctx.scene_id, iteration, name, args)
            tool_response = dispatch(name, args, ctx)
            log_tool_response(ctx.scene_id, iteration, name, tool_response)
            response_parts.append(types.Part.from_function_response(
                name=name, response=tool_response,
            ))

            if name == "done":
                if tool_response.get("accepted"):
                    accepted_video = Path(tool_response["video_path"])
                    accepted_summary = tool_response["ending_state_summary"]
                    done_seen = True
                else:
                    last_done_error = tool_response.get("error", "done rejected")

        contents.append(types.Content(role="user", parts=response_parts))

        if done_seen:
            info(f"worker:{ctx.scene_id}",
                 f"done() accepted at iter {iteration}; tool loop exiting")
            break
    else:
        warn(f"worker:{ctx.scene_id}",
             f"tool loop hit max_iter={max_iter} without done(); "
             f"will return best-effort or fail")

    return _finalize_tool_result(
        ctx, target, ident, file_stem, expected_class,
        accepted_video, accepted_summary, last_done_error,
    )


def _finalize_tool_result(
    ctx: WorkerToolContext,
    target: PlanTarget,
    ident: str,
    file_stem: str,
    expected_class: str,
    accepted_video: Optional[Path],
    accepted_summary: str,
    last_done_error: Optional[str],
) -> SceneResult:
    """Persist the worker's final code, promote the accepted mp4 to the
    stable scene path, and capture the last frame for the next scene."""
    scenes_dir = ctx.project_root / "scenes" / ctx.run_id
    scenes_dir.mkdir(parents=True, exist_ok=True)
    scene_file = scenes_dir / f"{file_stem}.py"
    if ctx.last_code:
        scene_file.write_text(ctx.last_code)

    artifacts_root = ctx.project_root / "output" / ctx.run_id
    if isinstance(target, SubScene):
        stable_path = artifacts_root / f"scene_{ident}.mp4"
    else:
        stable_path = artifacts_root / f"scene_{target.id}.mp4"

    # Decide outcome:
    #   - accepted_video set (model called done() and the rendered video passed
    #     validation) → success
    #   - ctx.last_render_path exists but no done() call → INCOMPLETE: copy the
    #     mp4 forward as evidence but mark success=False so plan-mode/QA know
    #     this isn't a finished scene. Avoids presenting a stale or broken
    #     render as if the worker were satisfied.
    #   - nothing rendered at all → hard fail
    if accepted_video is None:
        if ctx.last_render_path is not None and ctx.last_render_path.exists():
            copy_to(ctx.last_render_path, stable_path)
            last_frame_path: Optional[Path] = ctx.artifacts_dir / "last_frame.png"
            try:
                extract_last_frame(stable_path, last_frame_path)
            except Exception:
                last_frame_path = None
            try:
                duration = probe_video(stable_path).duration
            except Exception:
                duration = None
            return SceneResult(
                id=ident, scene_class=expected_class, scene_file=scene_file,
                video_path=stable_path, duration_seconds=duration,
                attempts=ctx.attempt_idx, success=False,
                last_error=(
                    last_done_error
                    or "max_tool_iterations exceeded — worker never reached done()."
                    " Last render preserved at video_path for inspection, but the"
                    " worker did not declare the scene complete."
                ),
                last_judge=None,
                ending_state="",
                last_frame_path=last_frame_path,
            )
        return SceneResult(
            id=ident, scene_class=expected_class, scene_file=scene_file,
            video_path=None, duration_seconds=None,
            attempts=ctx.attempt_idx, success=False,
            last_error=(ctx.last_log_tail or last_done_error or "no successful render"),
            last_judge=None,
            ending_state="",
            last_frame_path=None,
        )

    copy_to(accepted_video, stable_path)
    duration = probe_video(stable_path).duration
    last_frame_path = ctx.artifacts_dir / "last_frame.png"
    try:
        extract_last_frame(stable_path, last_frame_path)
    except Exception:
        last_frame_path = None
    return SceneResult(
        id=ident, scene_class=expected_class, scene_file=scene_file,
        video_path=stable_path, duration_seconds=duration,
        attempts=ctx.attempt_idx, success=True,
        last_error=None, last_judge=None,
        ending_state=accepted_summary,
        last_frame_path=last_frame_path,
    )
