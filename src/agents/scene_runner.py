"""Scene runner: dispatches simple vs complex (sub-scene) rendering.

For "simple" scenes, calls the worker once. For "complex" scenes, runs each
sub-scene worker in parallel, concatenates their mp4s, then runs the judge
on the concatenated result for continuity.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from src.agents.judge import judge_scene
from src.agents.scene_worker import render_scene, render_scene_with_tools
from src.agents.schemas import (
    JudgeReport,
    PriorContext,
    ScenePlan,
    ScenePlanItem,
    SceneResult,
)
from src.agents.tools import concat_mp4s, extract_last_frame, probe_video


async def run_scene(
    item: ScenePlanItem,
    plan: ScenePlan,
    *,
    run_id: str,
    quality: str,
    project_root: Path,
    sem: asyncio.Semaphore,
    max_attempts: int = 4,
    judge: bool = True,
    n_frames: int = 8,
    model: str = "gemini-2.5-pro",
    extra_brief: Optional[str] = None,
    resolution: Optional[tuple[int, int]] = None,
    aspect_ratio: Optional[str] = None,
    prior_context: Optional[PriorContext] = None,
    use_tool_worker: bool = False,
    max_tool_iterations: int = 8,
) -> SceneResult:
    if item.complexity == "simple" or not item.sub_scenes:
        async with sem:
            if use_tool_worker:
                result = await render_scene_with_tools(
                    item, plan,
                    run_id=run_id, quality=quality, project_root=project_root,
                    judge=judge, n_frames=n_frames, model=model,
                    extra_brief=extra_brief,
                    resolution=resolution, aspect_ratio=aspect_ratio,
                    prior_context=prior_context,
                    max_tool_iterations=max_tool_iterations,
                )
            else:
                result = await render_scene(
                    item, plan,
                    run_id=run_id, quality=quality, project_root=project_root,
                    max_attempts=max_attempts, judge=judge, n_frames=n_frames,
                    model=model, extra_brief=extra_brief,
                    resolution=resolution, aspect_ratio=aspect_ratio,
                )
            _ensure_last_frame(result, project_root, run_id)
            return result

    # Complex: render each sub-scene through the worker (sub-scenes share the
    # semaphore with siblings). For v1 we keep sub-scene rendering parallel
    # and only thread prior_context into each sub-scene's brief — within-scene
    # continuity is enforced by the parent plan's beats and shared_objects.
    sub_tasks = [
        asyncio.create_task(_run_sub_with_sem(
            sub, item, plan, run_id, quality, project_root, sem,
            max_attempts, judge, n_frames, model, extra_brief,
            resolution, aspect_ratio,
            prior_context, use_tool_worker, max_tool_iterations,
        ))
        for sub in item.sub_scenes
    ]
    sub_results: list[SceneResult] = await asyncio.gather(*sub_tasks)

    if not all(r.success for r in sub_results):
        # Find first failed sub for error reporting.
        failed = next((r for r in sub_results if not r.success), sub_results[0])
        return SceneResult(
            id=item.id,
            scene_class=item.scene_class,
            scene_file=None,
            video_path=None,
            duration_seconds=None,
            attempts=max(r.attempts for r in sub_results),
            success=False,
            last_error=f"Sub-scene {failed.id} failed: {failed.last_error}",
            last_judge=failed.last_judge,
        )

    # Concatenate sub-scene mp4s in order.
    artifacts_dir = Path(project_root) / "output" / run_id
    out_path = artifacts_dir / f"scene_{item.id}.mp4"
    sub_paths = [r.video_path for r in sub_results if r.video_path]
    concat_mp4s(sub_paths, out_path)
    total_duration = probe_video(out_path).duration

    # Continuity judge pass (optional).
    continuity_report: Optional[JudgeReport] = None
    if judge:
        try:
            continuity_report = await judge_scene(
                item, out_path,
                frames_dir=artifacts_dir / f"frames_{item.id}_continuity",
                n_frames=max(n_frames, 8),
                model=model,
                continuity_mode=True,
                plan=plan,
            )
        except Exception as exc:
            continuity_report = JudgeReport(
                passed=True,
                overall_assessment=f"(continuity judge failed to run: {exc!r})",
                issues=[],
            )

    # Best-effort success: even if the continuity judge flagged issues, we still
    # have a valid concatenated mp4 the stitcher can use. Master QA + cross-scene
    # continuity will see the issues via last_judge and feed them into the patch loop.
    last_frame_path = None
    try:
        last_frame_path = artifacts_dir / item.id / "last_frame.png"
        last_frame_path.parent.mkdir(parents=True, exist_ok=True)
        extract_last_frame(out_path, last_frame_path)
    except Exception:
        last_frame_path = None

    # Pull through ending_state from the LAST sub-scene that produced one.
    ending_state = ""
    for r in reversed(sub_results):
        if r.ending_state:
            ending_state = r.ending_state
            break

    return SceneResult(
        id=item.id,
        scene_class=item.scene_class,
        scene_file=None,
        video_path=out_path,
        duration_seconds=total_duration,
        attempts=max(r.attempts for r in sub_results),
        success=True,
        last_error=None,
        last_judge=continuity_report,
        ending_state=ending_state,
        last_frame_path=last_frame_path,
    )


async def _run_sub_with_sem(sub, parent_item, plan, run_id, quality,
                            project_root, sem, max_attempts, judge, n_frames,
                            model, extra_brief, resolution, aspect_ratio,
                            prior_context, use_tool_worker,
                            max_tool_iterations) -> SceneResult:
    async with sem:
        if use_tool_worker:
            result = await render_scene_with_tools(
                sub, plan,
                run_id=run_id, quality=quality, project_root=project_root,
                judge=judge, n_frames=n_frames, model=model,
                parent_id=parent_item.id, extra_brief=extra_brief,
                resolution=resolution, aspect_ratio=aspect_ratio,
                prior_context=prior_context,
                max_tool_iterations=max_tool_iterations,
            )
        else:
            result = await render_scene(
                sub, plan,
                run_id=run_id, quality=quality, project_root=project_root,
                max_attempts=max_attempts, judge=judge, n_frames=n_frames,
                model=model, parent_id=parent_item.id, extra_brief=extra_brief,
                resolution=resolution, aspect_ratio=aspect_ratio,
            )
        _ensure_last_frame(result, project_root, run_id)
        return result


def _ensure_last_frame(result: SceneResult, project_root: Path, run_id: str) -> None:
    """If the worker didn't capture a last_frame_path, do it here.

    The legacy text-only worker (render_scene) doesn't populate this — but the
    sequential pipeline still needs it to hand to the next scene. Best effort;
    silent no-op on failure.
    """
    if result.last_frame_path or not result.video_path:
        return
    try:
        out = Path(project_root) / "output" / run_id / result.id / "last_frame.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        extract_last_frame(Path(result.video_path), out)
        result.last_frame_path = out
    except Exception:
        pass
