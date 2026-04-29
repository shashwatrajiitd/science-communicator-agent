"""Cross-scene continuity check.

After all scenes are rendered, this module compares adjacent scene boundaries
(last frame of scene N vs first frame of scene N+1) using Gemini multimodal
vision. Mismatches in shared objects (different triangle orientation, different
colors, different labels for the same thing) are flagged as `continuity_*`
issues that the master QA loop feeds into the patch loop as `extra_brief`.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from src.agents.schemas import ScenePlan

load_dotenv()


CONTINUITY_PROMPT = r"""You are checking visual continuity between two
consecutive scenes of an explainer video.

You'll see two images:
  - Image A: the LAST frame of scene N
  - Image B: the FIRST frame of scene N+1

The brief lists the `shared_objects` that should appear in both scenes — these
must look IDENTICAL across the boundary: same shape, same orientation, same
color, same label, same approximate position.

Common failure modes:
  - Same object drawn with different geometry (right-angle triangle vs acute).
  - Same object drawn with different color or labels.
  - Object appears in scene N but is missing or renamed in N+1.
  - Different visual style (filled vs outline) for what is meant to be the
    same object.

For every mismatch, emit a JudgeIssue with:
  - kind: one of "continuity_geometry", "continuity_color", "continuity_label",
    "continuity_missing", "continuity_style".
  - severity: "high" if the audience would notice and be confused, "medium"
    for subtle mismatches, "low" for cosmetic.
  - where: identify which scene (N or N+1) needs to change. Prefer to fix
    N+1 to match N (since narrative flows forward).
  - description: what specifically differs.
  - fix_hint: ACTIONABLE instruction. e.g. "Scene 04 must redraw the unrolled
    triangle exactly as in scene 03: right-angled triangle with vertices
    (-pi*r, 0), (pi*r, 0), (-pi*r, r), color BLUE. Use Polygon with explicit
    vertices, not a generic Triangle()."

If everything matches, set passed=True with empty issues.

Output a JudgeReport JSON object. No prose, no fences.
"""


def _client():
    from google import genai
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in .env.")
    return genai.Client(api_key=api_key)


def _extract_one_frame(video_path: Path, timestamp: float, out_path: Path) -> Optional[Path]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{timestamp:.3f}", "-i", str(video_path),
         "-frames:v", "1", "-q:v", "2", str(out_path)],
        capture_output=True, text=True,
    )
    if proc.returncode == 0 and out_path.exists():
        return out_path
    return None


def _scene_duration(video_path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True, check=True,
    )
    return float(proc.stdout.strip())


async def check_continuity(
    plan: ScenePlan,
    scene_videos: dict[str, Path],
    *,
    artifacts_dir: Path,
    model: str = "gemini-2.5-pro",
) -> list[dict]:
    """Compare every adjacent scene pair. Return a list of QA-style issue dicts.

    `scene_videos` maps scene_id -> mp4 path. Only scenes present in the dict
    are checked (we skip scenes that failed entirely).
    """
    artifacts_dir = Path(artifacts_dir)
    boundary_dir = artifacts_dir / "continuity_frames"
    boundary_dir.mkdir(parents=True, exist_ok=True)

    ordered_ids = [s.id for s in plan.scenes if s.id in scene_videos]
    if len(ordered_ids) < 2:
        return []

    issues: list[dict] = []
    tasks = []
    pair_meta = []
    for a_id, b_id in zip(ordered_ids, ordered_ids[1:]):
        a_path = scene_videos[a_id]
        b_path = scene_videos[b_id]
        a_dur = _scene_duration(a_path)
        # Sample 0.3s before end for "last" and 0.3s in for "first".
        last_t = max(0.0, a_dur - 0.3)
        first_t = 0.3
        a_frame = _extract_one_frame(a_path, last_t, boundary_dir / f"end_of_{a_id}.png")
        b_frame = _extract_one_frame(b_path, first_t, boundary_dir / f"start_of_{b_id}.png")
        if a_frame is None or b_frame is None:
            continue

        # Find shared objects that appear in BOTH scenes.
        a_shared = {o.name for o in plan.shared_objects_for_scene(a_id)}
        b_shared = {o.name for o in plan.shared_objects_for_scene(b_id)}
        shared_in_pair = [o for o in plan.shared_objects if o.name in (a_shared & b_shared)]
        if not shared_in_pair:
            # No declared shared objects between these two — skip.
            # (We could still check, but it would surface false positives.)
            continue

        tasks.append(asyncio.to_thread(
            _call_continuity, model, plan, a_id, b_id, shared_in_pair, a_frame, b_frame
        ))
        pair_meta.append((a_id, b_id))

    results = await asyncio.gather(*tasks)
    for (a_id, b_id), result_json in zip(pair_meta, results):
        try:
            data = json.loads(result_json)
        except json.JSONDecodeError:
            continue
        for issue in data.get("issues", []):
            target_scene = b_id  # default: fix the later scene
            if "scene" in issue.get("where", "").lower() and a_id in issue["where"]:
                target_scene = a_id
            issues.append({
                "scene_id": target_scene,
                "kind": issue.get("kind", "continuity_geometry"),
                "severity": issue.get("severity", "medium"),
                "fix_hint": (
                    f"[continuity {a_id}->{b_id}] {issue.get('description', '')} "
                    f"FIX: {issue.get('fix_hint', '')}"
                ),
            })

    # Persist a summary
    (artifacts_dir / "continuity.json").write_text(json.dumps({
        "pairs_checked": [list(p) for p in pair_meta],
        "issues": issues,
    }, indent=2))
    return issues


def _call_continuity(model: str, plan: ScenePlan, a_id: str, b_id: str,
                     shared: list, a_frame: Path, b_frame: Path) -> str:
    from google.genai import types
    from src.agents.schemas import JUDGE_REPORT_SCHEMA

    shared_block = "\n".join(
        f"  - name: {o.name}\n"
        f"    color: {o.color}\n"
        f"    label: {o.label!r}\n"
        f"    spec: {o.spec}"
        for o in shared
    )
    user_text = (
        f"Scene N = {a_id}, scene N+1 = {b_id}.\n\n"
        f"shared_objects that must look identical in both:\n{shared_block}\n\n"
        f"Image A is the last frame of scene {a_id}.\n"
        f"Image B is the first frame of scene {b_id}.\n\n"
        "Compare the two frames and emit a JudgeReport listing any continuity "
        "mismatches in the shared objects. If `where` mentions a scene id, "
        "use the form 'scene 04' or 'scene 03'."
    )
    parts = [
        types.Part.from_bytes(data=a_frame.read_bytes(), mime_type="image/png"),
        types.Part.from_bytes(data=b_frame.read_bytes(), mime_type="image/png"),
        types.Part.from_text(text=user_text),
    ]
    contents = [types.Content(role="user", parts=parts)]

    client = _client()
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=CONTINUITY_PROMPT,
            response_mime_type="application/json",
            response_schema=JUDGE_REPORT_SCHEMA,
            temperature=0.2,
        ),
    )
    return response.text or "{}"
