"""Dataclasses + Gemini structured-output schemas for the multi-agent pipeline.

The dataclasses are the in-memory representation. The `*_RESPONSE_SCHEMA` dicts
are passed to `genai.Client.generate_content(... response_schema=...)` so the
model returns valid JSON that round-trips through `from_dict`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Plan schemas
# ---------------------------------------------------------------------------

@dataclass
class NarrationBeat:
    text: str
    animation_hint: str

    @staticmethod
    def from_dict(d: dict) -> "NarrationBeat":
        return NarrationBeat(text=d["text"], animation_hint=d["animation_hint"])


@dataclass
class SubScene:
    id: str
    slug: str
    description: str
    beats: list[NarrationBeat]
    target_seconds: float
    key_visuals: list[str]
    correctness_checks: list[str]

    @staticmethod
    def from_dict(d: dict) -> "SubScene":
        return SubScene(
            id=d["id"],
            slug=d["slug"],
            description=d["description"],
            beats=[NarrationBeat.from_dict(b) for b in d.get("beats", [])],
            target_seconds=float(d["target_seconds"]),
            key_visuals=list(d.get("key_visuals", [])),
            correctness_checks=list(d.get("correctness_checks", [])),
        )


@dataclass
class ScenePlanItem:
    id: str
    slug: str
    description: str
    target_seconds: float
    key_visuals: list[str]
    complexity: str  # "simple" | "complex"
    correctness_checks: list[str] = field(default_factory=list)
    beats: Optional[list[NarrationBeat]] = None
    sub_scenes: Optional[list[SubScene]] = None

    @staticmethod
    def from_dict(d: dict) -> "ScenePlanItem":
        beats = [NarrationBeat.from_dict(b) for b in d["beats"]] if d.get("beats") else None
        subs = [SubScene.from_dict(s) for s in d["sub_scenes"]] if d.get("sub_scenes") else None
        return ScenePlanItem(
            id=d["id"],
            slug=d["slug"],
            description=d["description"],
            target_seconds=float(d["target_seconds"]),
            key_visuals=list(d.get("key_visuals", [])),
            complexity=d.get("complexity", "simple"),
            correctness_checks=list(d.get("correctness_checks", [])),
            beats=beats,
            sub_scenes=subs,
        )

    @property
    def scene_class(self) -> str:
        return _slug_to_class(self.slug)


@dataclass
class ScenePlan:
    topic: str
    title: str
    total_target_seconds: float
    voice: str
    scenes: list[ScenePlanItem]

    @staticmethod
    def from_dict(d: dict) -> "ScenePlan":
        return ScenePlan(
            topic=d["topic"],
            title=d["title"],
            total_target_seconds=float(d["total_target_seconds"]),
            voice=d.get("voice", "Aoede"),
            scenes=[ScenePlanItem.from_dict(s) for s in d["scenes"]],
        )

    def to_dict(self) -> dict:
        return _to_serializable(asdict(self))


# ---------------------------------------------------------------------------
# Worker / runner result
# ---------------------------------------------------------------------------

@dataclass
class JudgeIssue:
    kind: str
    severity: str  # "low" | "medium" | "high"
    where: str
    description: str
    fix_hint: str

    @staticmethod
    def from_dict(d: dict) -> "JudgeIssue":
        return JudgeIssue(
            kind=d.get("kind", "other"),
            severity=d.get("severity", "medium"),
            where=d.get("where", ""),
            description=d.get("description", ""),
            fix_hint=d.get("fix_hint", ""),
        )


@dataclass
class JudgeReport:
    passed: bool
    overall_assessment: str
    issues: list[JudgeIssue] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "JudgeReport":
        return JudgeReport(
            passed=bool(d.get("passed", False)),
            overall_assessment=d.get("overall_assessment", ""),
            issues=[JudgeIssue.from_dict(i) for i in d.get("issues", [])],
        )

    def to_dict(self) -> dict:
        return _to_serializable(asdict(self))


@dataclass
class SceneResult:
    id: str
    scene_class: str
    scene_file: Optional[Path]
    video_path: Optional[Path]
    duration_seconds: Optional[float]
    attempts: int
    success: bool
    last_error: Optional[str] = None
    last_judge: Optional[JudgeReport] = None

    def to_dict(self) -> dict:
        return _to_serializable(asdict(self))


# ---------------------------------------------------------------------------
# Master QA
# ---------------------------------------------------------------------------

@dataclass
class QAIssue:
    scene_id: str  # "01", "02", ... or "global"
    kind: str
    severity: str
    fix_hint: str

    @staticmethod
    def from_dict(d: dict) -> "QAIssue":
        return QAIssue(
            scene_id=d.get("scene_id", "global"),
            kind=d.get("kind", "other"),
            severity=d.get("severity", "medium"),
            fix_hint=d.get("fix_hint", ""),
        )


@dataclass
class QAReport:
    overall_ok: bool
    issues: list[QAIssue] = field(default_factory=list)
    notes: str = ""

    @staticmethod
    def from_dict(d: dict) -> "QAReport":
        return QAReport(
            overall_ok=bool(d.get("overall_ok", False)),
            issues=[QAIssue.from_dict(i) for i in d.get("issues", [])],
            notes=d.get("notes", ""),
        )

    def to_dict(self) -> dict:
        return _to_serializable(asdict(self))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug_to_class(slug: str) -> str:
    """fourier_intuition -> FourierIntuition. Sub-scene slugs may contain '__'."""
    parts = slug.replace("__", "_").split("_")
    return "".join(p.capitalize() for p in parts if p) or "GeneratedScene"


def _to_serializable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


# ---------------------------------------------------------------------------
# JSON schemas for Gemini structured output (response_schema=)
# ---------------------------------------------------------------------------
#
# Kept deliberately minimal — Gemini's structured-output constraint solver
# rejects schemas with too many states (long enums, deep nesting, minItems/
# maxItems, propertyOrdering all add states). We rely on the prompt for fine
# structure (e.g. number of beats, voice choice) and on the schema only for
# the JSON shape the parser needs.

_NARRATION_BEAT_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "animation_hint": {"type": "string"},
    },
    "required": ["text", "animation_hint"],
}

_SUB_SCENE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "slug": {"type": "string"},
        "description": {"type": "string"},
        "beats": {"type": "array", "items": _NARRATION_BEAT_SCHEMA},
        "target_seconds": {"type": "number"},
        "key_visuals": {"type": "array", "items": {"type": "string"}},
        "correctness_checks": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "slug", "description", "beats", "target_seconds"],
}

_SCENE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "slug": {"type": "string"},
        "description": {"type": "string"},
        "target_seconds": {"type": "number"},
        "key_visuals": {"type": "array", "items": {"type": "string"}},
        "complexity": {"type": "string"},
        "correctness_checks": {"type": "array", "items": {"type": "string"}},
        "beats": {"type": "array", "items": _NARRATION_BEAT_SCHEMA},
        "sub_scenes": {"type": "array", "items": _SUB_SCENE_SCHEMA},
    },
    "required": ["id", "slug", "description", "target_seconds", "complexity"],
}

SCENE_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "title": {"type": "string"},
        "total_target_seconds": {"type": "number"},
        "voice": {"type": "string"},
        "scenes": {"type": "array", "items": _SCENE_ITEM_SCHEMA},
    },
    "required": ["topic", "title", "total_target_seconds", "voice", "scenes"],
}

_JUDGE_ISSUE_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string"},
        "severity": {"type": "string"},
        "where": {"type": "string"},
        "description": {"type": "string"},
        "fix_hint": {"type": "string"},
    },
    "required": ["kind", "severity", "description", "fix_hint"],
}

JUDGE_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "passed": {"type": "boolean"},
        "overall_assessment": {"type": "string"},
        "issues": {"type": "array", "items": _JUDGE_ISSUE_SCHEMA},
    },
    "required": ["passed", "overall_assessment", "issues"],
}

_QA_ISSUE_SCHEMA = {
    "type": "object",
    "properties": {
        "scene_id": {"type": "string"},
        "kind": {"type": "string"},
        "severity": {"type": "string"},
        "fix_hint": {"type": "string"},
    },
    "required": ["scene_id", "kind", "severity", "fix_hint"],
}

QA_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_ok": {"type": "boolean"},
        "issues": {"type": "array", "items": _QA_ISSUE_SCHEMA},
        "notes": {"type": "string"},
    },
    "required": ["overall_ok", "issues", "notes"],
}
