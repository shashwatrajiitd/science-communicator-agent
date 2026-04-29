"""Master planner + QA agents.

Implemented with plain `google-genai` (Gemini Structured Output via
`response_schema`). The agents are exposed as awaitable Python functions —
the rest of the pipeline orchestrates them with asyncio.

We use ADK only conceptually here (planner/QA are "agents" in the architectural
sense). They don't need ADK's tool-calling machinery — their job is to emit
structured JSON. The Judge agent (which uses multimodal vision) lives in
judge.py and follows the same pattern.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Optional

from dotenv import load_dotenv

from src.agents.prompts import (
    MASTER_PLAN_REVISION_PROMPT,
    MASTER_PLANNER_PROMPT,
    MASTER_QA_PROMPT,
)
from src.agents.schemas import (
    QA_REPORT_SCHEMA,
    QAReport,
    SCENE_PLAN_SCHEMA,
    ScenePlan,
)

load_dotenv()


def _client():
    from google import genai
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in .env.")
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

async def plan_video(topic: str, *, model: str = "gemini-2.5-pro",
                     scene_count_hint: Optional[int] = None,
                     allow_decomposition: bool = True) -> ScenePlan:
    """Ask Gemini for a structured ScenePlan."""
    user_msg = f"Topic: {topic}"
    if scene_count_hint:
        user_msg += f"\nTarget number of top-level scenes: {scene_count_hint}"
    if not allow_decomposition:
        user_msg += "\nDo NOT use complex/sub_scenes — every scene must be `simple`."

    json_text = await asyncio.to_thread(_call_planner, model, user_msg)
    data = json.loads(json_text)
    plan = ScenePlan.from_dict(data)
    _validate_plan(plan, allow_decomposition)
    return plan


def _call_planner(model: str, user_msg: str) -> str:
    from google.genai import types
    client = _client()
    response = client.models.generate_content(
        model=model,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=MASTER_PLANNER_PROMPT,
            response_mime_type="application/json",
            response_schema=SCENE_PLAN_SCHEMA,
            temperature=0.7,
        ),
    )
    return response.text or "{}"


def _validate_plan(plan: ScenePlan, allow_decomposition: bool) -> None:
    if not plan.scenes:
        raise ValueError("Planner returned no scenes.")
    seen_ids: set[str] = set()
    for scene in plan.scenes:
        if scene.id in seen_ids:
            raise ValueError(f"Duplicate scene id {scene.id}.")
        seen_ids.add(scene.id)
        if scene.complexity == "complex":
            if not allow_decomposition:
                # Coerce to simple if decomposition was disabled.
                scene.complexity = "simple"
                if not scene.beats and scene.sub_scenes:
                    scene.beats = []
                    for sub in scene.sub_scenes:
                        scene.beats.extend(sub.beats or [])
                    scene.sub_scenes = None
            else:
                if not scene.sub_scenes:
                    raise ValueError(f"Scene {scene.id} marked complex but has no sub_scenes.")
                for sub in scene.sub_scenes:
                    if not sub.beats:
                        raise ValueError(f"Sub-scene {scene.id}/{sub.id} has no beats.")
        else:
            if not scene.beats:
                raise ValueError(f"Simple scene {scene.id} has no beats.")


# ---------------------------------------------------------------------------
# Plan revision (used by --plan-mode)
# ---------------------------------------------------------------------------

async def revise_plan(plan: ScenePlan, feedback: str, *,
                      model: str = "gemini-2.5-pro") -> ScenePlan:
    """Rewrite a ScenePlan in light of one line of operator feedback.

    Re-uses SCENE_PLAN_SCHEMA, so the returned object round-trips through
    `ScenePlan.from_dict`. The system prompt instructs the model to apply
    the feedback exactly and preserve everything else.
    """
    payload = json.dumps({"plan": plan.to_dict(), "feedback": feedback}, indent=2)
    json_text = await asyncio.to_thread(_call_revise_plan, model, payload)
    revised = ScenePlan.from_dict(json.loads(json_text))
    _validate_plan(revised, allow_decomposition=True)
    return revised


def _call_revise_plan(model: str, payload: str) -> str:
    from google.genai import types
    client = _client()
    response = client.models.generate_content(
        model=model,
        contents=payload,
        config=types.GenerateContentConfig(
            system_instruction=MASTER_PLAN_REVISION_PROMPT,
            response_mime_type="application/json",
            response_schema=SCENE_PLAN_SCHEMA,
            temperature=0.5,
        ),
    )
    return response.text or "{}"


# ---------------------------------------------------------------------------
# Master QA
# ---------------------------------------------------------------------------

async def qa_review(plan: ScenePlan, results: list[dict],
                    deterministic_issues: list[dict],
                    *, model: str = "gemini-2.5-pro") -> QAReport:
    """Run the master QA pass. `results` is list of SceneResult.to_dict()."""
    user_msg = json.dumps({
        "plan": plan.to_dict(),
        "results": results,
        "deterministic_issues": deterministic_issues,
    }, indent=2)
    json_text = await asyncio.to_thread(_call_qa, model, user_msg)
    return QAReport.from_dict(json.loads(json_text))


def _call_qa(model: str, user_msg: str) -> str:
    from google.genai import types
    client = _client()
    response = client.models.generate_content(
        model=model,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=MASTER_QA_PROMPT,
            response_mime_type="application/json",
            response_schema=QA_REPORT_SCHEMA,
            temperature=0.3,
        ),
    )
    return response.text or "{}"


# ---------------------------------------------------------------------------
# Deterministic per-scene checks (cheap, no LLM)
# ---------------------------------------------------------------------------

def deterministic_qa(plan: ScenePlan, results: list[dict]) -> list[dict]:
    """Computed in Python — feeds into the LLM QA call as context."""
    issues: list[dict] = []
    by_id = {r["id"]: r for r in results}
    for scene in plan.scenes:
        r = by_id.get(scene.id)
        if not r:
            issues.append({
                "scene_id": scene.id,
                "kind": "render_error",
                "severity": "high",
                "fix_hint": "Scene was never rendered.",
            })
            continue
        if not r.get("success"):
            issues.append({
                "scene_id": scene.id,
                "kind": "render_error",
                "severity": "high",
                "fix_hint": (r.get("last_error") or "")[:400] or "Scene failed all retries.",
            })
            continue
        dur = r.get("duration_seconds")
        if dur and scene.target_seconds:
            drift = abs(dur - scene.target_seconds) / scene.target_seconds
            if drift > 0.4:
                issues.append({
                    "scene_id": scene.id,
                    "kind": "duration_mismatch",
                    "severity": "medium" if drift < 0.7 else "high",
                    "fix_hint": (
                        f"measured {dur:.1f}s vs target {scene.target_seconds:.1f}s "
                        f"({drift*100:.0f}% drift). Adjust narration length."
                    ),
                })
    # Total drift
    total_meas = sum((by_id.get(s.id, {}) or {}).get("duration_seconds") or 0 for s in plan.scenes)
    if plan.total_target_seconds:
        total_drift = abs(total_meas - plan.total_target_seconds) / plan.total_target_seconds
        if total_drift > 0.3:
            issues.append({
                "scene_id": "global",
                "kind": "duration_mismatch",
                "severity": "low",
                "fix_hint": (
                    f"total {total_meas:.1f}s vs target {plan.total_target_seconds:.1f}s "
                    f"({total_drift*100:.0f}% drift)."
                ),
            })
    return issues
