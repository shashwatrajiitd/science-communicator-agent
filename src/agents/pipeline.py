"""Top-level orchestrator for the multi-agent video pipeline."""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.agents.continuity import check_continuity
from src.agents.master import deterministic_qa, plan_video, qa_review
from src.agents.scene_runner import run_scene
from src.agents.schemas import PriorContext, ScenePlan, SceneResult
from src.agents.tools import concat_mp4s, parse_aspect_ratio, probe_video, resolution_for


PROJECT_ROOT = Path(__file__).resolve().parents[2]


async def run(
    topic: str,
    *,
    quality: str = "l",
    run_id: Optional[str] = None,
    parallelism: int = 4,
    max_attempts: int = 4,
    patch_passes: int = 2,
    qa_enabled: bool = True,
    judge: bool = True,
    n_frames: int = 8,
    allow_decomposition: bool = True,
    scene_count_hint: Optional[int] = None,
    voice_override: Optional[str] = None,
    model: str = "gemini-2.5-pro",
    aspect_ratio: str = "16:9",
    parallel: bool = False,
    use_tool_worker: bool = True,
    max_tool_iterations: int = 12,
    adviser_model: Optional[str] = None,
    escalate_after_render_failures: int = 5,
    video_review_enabled: bool = True,
    max_review_rounds: int = 2,
    video_review_model: str = "gemini-2.5-pro",
    log: Optional[callable] = None,
    pre_plan_approval: Optional[callable] = None,
    post_scene_approval: Optional[callable] = None,
) -> Path:
    """Run the full pipeline. Returns path to final mp4."""
    log = log or print

    if run_id is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(topic)[:40]
        run_id = f"{ts}_{slug}"

    aspect_tuple = parse_aspect_ratio(aspect_ratio)
    resolution = resolution_for(aspect_tuple, quality)

    artifacts_dir = PROJECT_ROOT / "output" / run_id
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    log(f"[pipeline] run_id={run_id}  artifacts={artifacts_dir}")
    log(f"[pipeline] aspect_ratio={aspect_ratio}  resolution={resolution[0]}x{resolution[1]}")
    log(f"[pipeline] mode={'parallel' if parallel else 'sequential'}  use_tool_worker={use_tool_worker}")

    # ----- Phase 1: Plan -----
    t0 = time.time()
    log(f"[pipeline] planning topic with model={model}...")
    plan = await plan_video(
        topic, model=model,
        scene_count_hint=scene_count_hint,
        allow_decomposition=allow_decomposition,
    )
    if voice_override:
        plan.voice = voice_override
    (artifacts_dir / "plan.json").write_text(json.dumps(plan.to_dict(), indent=2))
    log(f"[pipeline] plan: {len(plan.scenes)} scenes, total_target={plan.total_target_seconds}s, voice={plan.voice}  ({time.time()-t0:.1f}s)")

    # Optional plan-approval gate (Phase 3). Default no-op pass-through.
    if pre_plan_approval is not None:
        plan = await _maybe_await(pre_plan_approval(plan))
        (artifacts_dir / "plan.json").write_text(json.dumps(plan.to_dict(), indent=2))

    # ----- Phase 2: Render scenes -----
    sem = asyncio.Semaphore(parallelism if parallel else 1)
    log(
        f"[pipeline] rendering {len(plan.scenes)} scenes "
        f"(mode={'parallel' if parallel else 'sequential'}, "
        f"parallelism={parallelism if parallel else 1}, judge={judge})..."
    )
    t1 = time.time()
    if parallel:
        results: list[SceneResult] = await asyncio.gather(*[
            run_scene(
                item, plan,
                run_id=run_id, quality=quality, project_root=PROJECT_ROOT,
                sem=sem, max_attempts=max_attempts, judge=judge, n_frames=n_frames,
                model=model,
                resolution=resolution, aspect_ratio=aspect_ratio,
                use_tool_worker=use_tool_worker,
                max_tool_iterations=max_tool_iterations,
                adviser_model=adviser_model,
                escalate_after_render_failures=escalate_after_render_failures,
                video_review_enabled=video_review_enabled,
                max_review_rounds=max_review_rounds,
                video_review_model=video_review_model,
            )
            for item in plan.scenes
        ])
    else:
        results = []
        prior: Optional[PriorContext] = None
        for item in plan.scenes:
            current_prior = prior  # captured by the rerun closure below
            r = await run_scene(
                item, plan,
                run_id=run_id, quality=quality, project_root=PROJECT_ROOT,
                sem=sem, max_attempts=max_attempts, judge=judge, n_frames=n_frames,
                model=model,
                resolution=resolution, aspect_ratio=aspect_ratio,
                prior_context=current_prior,
                use_tool_worker=use_tool_worker,
                max_tool_iterations=max_tool_iterations,
                adviser_model=adviser_model,
                escalate_after_render_failures=escalate_after_render_failures,
                video_review_enabled=video_review_enabled,
                max_review_rounds=max_review_rounds,
                video_review_model=video_review_model,
            )
            if post_scene_approval is not None:
                async def _rerun(extra: Optional[str], _item=item,
                                 _prior=current_prior) -> SceneResult:
                    return await run_scene(
                        _item, plan,
                        run_id=run_id, quality=quality, project_root=PROJECT_ROOT,
                        sem=sem, max_attempts=max_attempts, judge=judge,
                        n_frames=n_frames, model=model,
                        resolution=resolution, aspect_ratio=aspect_ratio,
                        prior_context=_prior,
                        use_tool_worker=use_tool_worker,
                        max_tool_iterations=max_tool_iterations,
                        adviser_model=adviser_model,
                        escalate_after_render_failures=escalate_after_render_failures,
                        extra_brief=extra,
                        video_review_enabled=video_review_enabled,
                        max_review_rounds=max_review_rounds,
                        video_review_model=video_review_model,
                    )

                async def _translate_comment(_item, _result, _comment,
                                             _prior=current_prior) -> Optional[str]:
                    return await _translate_planmode_comment(
                        _item, _result, _comment,
                        plan=plan, prior_context=_prior,
                        artifacts_dir=artifacts_dir,
                        video_review_model=video_review_model,
                    )

                r = await _maybe_await(post_scene_approval(
                    item, r, _rerun,
                    _translate_comment if video_review_enabled else None,
                ))
            results.append(r)
            if r.success:
                prior = _build_prior_context(item, r)
    log(f"[pipeline] rendering done in {time.time()-t1:.1f}s")
    for r in results:
        status = "OK" if r.success else "FAIL"
        log(f"  scene {r.id}  {status}  attempts={r.attempts}  duration={r.duration_seconds}")

    # ----- Phase 3: Stitch -----
    final_path = _stitch(plan, results, artifacts_dir)
    log(f"[pipeline] stitched final.mp4 -> {final_path}")

    # ----- Phase 4: QA + auto-patch loop -----
    patch_log: list[dict] = []
    if qa_enabled:
        for patch_pass in range(1, patch_passes + 2):  # 0 = initial check, 1..patch_passes = patches
            det_issues = deterministic_qa(plan, [r.to_dict() for r in results])

            # Cross-scene continuity check (LLM vision on adjacent boundaries).
            scene_videos = {
                r.id: Path(r.video_path)
                for r in results if r.success and r.video_path and Path(r.video_path).exists()
            }
            continuity_issues: list[dict] = []
            if judge and len(scene_videos) >= 2 and plan.shared_objects:
                log(f"[pipeline] running continuity check across {len(scene_videos)} scenes...")
                try:
                    continuity_issues = await check_continuity(
                        plan, scene_videos,
                        artifacts_dir=artifacts_dir, model=model,
                    )
                    log(f"[pipeline] continuity issues: {len(continuity_issues)}")
                except Exception as exc:
                    log(f"[pipeline] continuity check failed: {exc!r}")
            all_det_issues = det_issues + continuity_issues
            log(f"[pipeline] QA pass {patch_pass}: {len(det_issues)} det + {len(continuity_issues)} continuity")

            qa_report = await qa_review(plan, [r.to_dict() for r in results], all_det_issues, model=model)
            (artifacts_dir / "qa.json").write_text(json.dumps(qa_report.to_dict(), indent=2))

            if qa_report.overall_ok and not [
                d for d in all_det_issues if d["severity"] in ("medium", "high")
            ]:
                log(f"[pipeline] QA passed.")
                break
            if patch_pass > patch_passes:
                log(f"[pipeline] QA still has issues, but patch budget exhausted.")
                break

            # Patch failing scenes — combine LLM QA hints + continuity hints
            id_to_hints: dict[str, list[str]] = {}
            for i in qa_report.issues:
                if i.scene_id != "global":
                    id_to_hints.setdefault(i.scene_id, []).append(i.fix_hint)
            for d in continuity_issues:
                if d["scene_id"] != "global":
                    id_to_hints.setdefault(d["scene_id"], []).append(d["fix_hint"])
            for d in det_issues:
                if d["scene_id"] != "global" and d["severity"] in ("medium", "high"):
                    id_to_hints.setdefault(d["scene_id"], []).append(d["fix_hint"])

            affected = sorted(id_to_hints.keys())
            if not affected:
                log(f"[pipeline] only global issues — nothing to patch.")
                break

            log(f"[pipeline] patch pass {patch_pass}: re-rendering scenes {affected}")
            id_to_item = {s.id: s for s in plan.scenes}
            patched_by_id: dict[str, SceneResult] = {}
            if parallel:
                sem2 = asyncio.Semaphore(parallelism)
                patch_tasks = []
                for sid in affected:
                    item = id_to_item.get(sid)
                    if item is None:
                        continue
                    combined_hint = "\n".join(id_to_hints[sid])
                    patch_tasks.append(run_scene(
                        item, plan,
                        run_id=run_id, quality=quality, project_root=PROJECT_ROOT,
                        sem=sem2, max_attempts=max_attempts, judge=judge,
                        n_frames=n_frames, model=model,
                        extra_brief=combined_hint,
                        resolution=resolution, aspect_ratio=aspect_ratio,
                        use_tool_worker=use_tool_worker,
                        max_tool_iterations=max_tool_iterations,
                        adviser_model=adviser_model,
                        escalate_after_render_failures=escalate_after_render_failures,
                        # Master QA already provided structured patch hints;
                        # running the per-scene reviewer on top would duplicate
                        # work and burn tokens. Single source of feedback.
                        video_review_enabled=False,
                        max_review_rounds=max_review_rounds,
                        video_review_model=video_review_model,
                    ))
                patched: list[SceneResult] = await asyncio.gather(*patch_tasks)
                patched_by_id = {r.id: r for r in patched}
            else:
                # Sequential patch: walk plan order; build prior_context from the
                # most recent result of each predecessor (patched or original).
                sem2 = asyncio.Semaphore(1)
                affected_set = set(affected)
                live: dict[str, SceneResult] = {r.id: r for r in results}
                prior_seq: Optional[PriorContext] = None
                for scene in plan.scenes:
                    if scene.id in affected_set:
                        combined_hint = "\n".join(id_to_hints[scene.id])
                        r = await run_scene(
                            scene, plan,
                            run_id=run_id, quality=quality, project_root=PROJECT_ROOT,
                            sem=sem2, max_attempts=max_attempts, judge=judge,
                            n_frames=n_frames, model=model,
                            extra_brief=combined_hint,
                            resolution=resolution, aspect_ratio=aspect_ratio,
                            prior_context=prior_seq,
                            use_tool_worker=use_tool_worker,
                            max_tool_iterations=max_tool_iterations,
                            adviser_model=adviser_model,
                            escalate_after_render_failures=escalate_after_render_failures,
                            video_review_enabled=False,
                            max_review_rounds=max_review_rounds,
                            video_review_model=video_review_model,
                        )
                        patched_by_id[scene.id] = r
                        live[scene.id] = r
                    if live[scene.id].success:
                        prior_seq = _build_prior_context(scene, live[scene.id])
            patch_log.append({
                "pass": patch_pass,
                "affected": affected,
                "hints": id_to_hints,
                "outcomes": {pid: r.success for pid, r in patched_by_id.items()},
            })
            # Replace results for affected scenes
            results = [patched_by_id.get(r.id, r) for r in results]
            final_path = _stitch(plan, results, artifacts_dir)
            log(f"[pipeline] re-stitched final.mp4 after patch pass {patch_pass}")

    (artifacts_dir / "patch_log.json").write_text(json.dumps(patch_log, indent=2))
    return final_path


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _stitch(plan: ScenePlan, results: list[SceneResult], artifacts_dir: Path) -> Path:
    by_id = {r.id: r for r in results}
    paths: list[Path] = []
    for scene in plan.scenes:
        r = by_id.get(scene.id)
        if r and r.success and r.video_path and Path(r.video_path).exists():
            paths.append(Path(r.video_path))
    if not paths:
        raise RuntimeError("No successful scenes to stitch.")
    out = artifacts_dir / "final.mp4"
    concat_mp4s(paths, out)
    return out


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s.lower()).strip("_")
    return s or "video"


def _build_prior_context(item, result: SceneResult) -> PriorContext:
    """Snapshot a successful scene's outcome for the next scene's worker."""
    return PriorContext(
        prior_scene_id=item.id,
        last_frame_path=result.last_frame_path,
        ending_state=result.ending_state or "",
        prior_code_path=result.scene_file,
    )


async def _maybe_await(value):
    """Await `value` if it is awaitable; otherwise return as-is.

    Lets pre_plan_approval / post_scene_approval hooks be either sync or async.
    """
    if asyncio.iscoroutine(value) or asyncio.isfuture(value):
        return await value
    return value


_PLANMODE_COMMENT_ROUND: dict[str, int] = {}


async def _translate_planmode_comment(
    item, result: SceneResult, comment: str,
    *, plan: ScenePlan, prior_context: Optional[PriorContext],
    artifacts_dir: Path, video_review_model: str,
) -> Optional[str]:
    """Send the rendered scene + operator comment to the video reviewer
    and return formatted prose hints. None on failure (caller falls back
    to passing the raw comment).

    Persists `video_review_planmode_<n>.json` next to the scene's other
    artifacts so the operator can audit what the reviewer said.
    """
    from src.agents.video_reviewer import (
        format_video_review_hints,
        review_scene_video,
    )

    if not result.video_path or not Path(result.video_path).exists():
        return None

    prior_last_frame = (
        prior_context.last_frame_path
        if prior_context is not None else None
    )
    prior_code = None
    if result.scene_file and Path(result.scene_file).exists():
        try:
            prior_code = Path(result.scene_file).read_text()
        except OSError:
            prior_code = None

    try:
        report = await asyncio.to_thread(
            review_scene_video,
            Path(result.video_path), item, plan,
            prior_last_frame=prior_last_frame,
            user_comment=comment,
            prior_code=prior_code,
            model=video_review_model,
            parent_scene_id=None,
        )
    except Exception:
        return None

    # Persist for audit. Round numbers are scene-scoped.
    _PLANMODE_COMMENT_ROUND[item.id] = _PLANMODE_COMMENT_ROUND.get(item.id, 0) + 1
    round_n = _PLANMODE_COMMENT_ROUND[item.id]
    out = artifacts_dir / item.id / f"video_review_planmode_{round_n}.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "operator_comment": comment,
            "round": round_n,
            "report": report.to_dict(),
        }
        out.write_text(json.dumps(payload, indent=2))
    except Exception:
        pass

    return format_video_review_hints(report)
