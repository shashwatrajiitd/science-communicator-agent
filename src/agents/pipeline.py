"""Top-level orchestrator for the multi-agent video pipeline."""

from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.agents.master import deterministic_qa, plan_video, qa_review
from src.agents.scene_runner import run_scene
from src.agents.schemas import ScenePlan, SceneResult
from src.agents.tools import concat_mp4s, probe_video


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
    log: Optional[callable] = None,
) -> Path:
    """Run the full pipeline. Returns path to final mp4."""
    log = log or print

    if run_id is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(topic)[:40]
        run_id = f"{ts}_{slug}"

    artifacts_dir = PROJECT_ROOT / "output" / run_id
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    log(f"[pipeline] run_id={run_id}  artifacts={artifacts_dir}")

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

    # ----- Phase 2: Render scenes (parallel) -----
    sem = asyncio.Semaphore(parallelism)
    log(f"[pipeline] rendering {len(plan.scenes)} scenes (parallelism={parallelism}, judge={judge})...")
    t1 = time.time()
    results: list[SceneResult] = await asyncio.gather(*[
        run_scene(
            item, plan,
            run_id=run_id, quality=quality, project_root=PROJECT_ROOT,
            sem=sem, max_attempts=max_attempts, judge=judge, n_frames=n_frames,
            model=model,
        )
        for item in plan.scenes
    ])
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
            log(f"[pipeline] QA pass {patch_pass}: {len(det_issues)} deterministic issues")
            qa_report = await qa_review(plan, [r.to_dict() for r in results], det_issues, model=model)
            (artifacts_dir / "qa.json").write_text(json.dumps(qa_report.to_dict(), indent=2))

            if qa_report.overall_ok and not [
                d for d in det_issues if d["severity"] in ("medium", "high")
            ]:
                log(f"[pipeline] QA passed.")
                break
            if patch_pass > patch_passes:
                log(f"[pipeline] QA still has issues, but patch budget exhausted.")
                break

            # Patch failing scenes
            affected = sorted({i.scene_id for i in qa_report.issues if i.scene_id != "global"})
            affected = affected or [
                d["scene_id"] for d in det_issues
                if d["scene_id"] != "global" and d["severity"] in ("medium", "high")
            ]
            if not affected:
                log(f"[pipeline] only global issues — nothing to patch.")
                break

            log(f"[pipeline] patch pass {patch_pass}: re-rendering scenes {affected}")
            id_to_hint = {i.scene_id: i.fix_hint for i in qa_report.issues}
            sem2 = asyncio.Semaphore(parallelism)
            id_to_item = {s.id: s for s in plan.scenes}
            patch_tasks = []
            for sid in affected:
                item = id_to_item.get(sid)
                if item is None:
                    continue
                patch_tasks.append(run_scene(
                    item, plan,
                    run_id=run_id, quality=quality, project_root=PROJECT_ROOT,
                    sem=sem2, max_attempts=max_attempts, judge=judge,
                    n_frames=n_frames, model=model,
                    extra_brief=id_to_hint.get(sid, ""),
                ))
            patched: list[SceneResult] = await asyncio.gather(*patch_tasks)
            patched_by_id = {r.id: r for r in patched}
            patch_log.append({
                "pass": patch_pass,
                "affected": affected,
                "hints": id_to_hint,
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
