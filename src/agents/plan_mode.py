"""Interactive plan + per-scene review for `--plan-mode`.

Builds the two callbacks `pipeline.run` accepts (`pre_plan_approval` and
`post_scene_approval`) and wraps them in a typer/rich UI:

  Phase 1 — display the planner's ScenePlan, prompt approve / comment / quit;
            on comment, call master.revise_plan and re-display.
  Phase 2 — after each scene renders, auto-open the mp4, prompt approve /
            comment / retry / quit; on comment, call rerun(extra_brief=...)
            with the operator's feedback.

All actions are appended to `output/<run_id>/reviews.jsonl` for audit.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.agents.master import revise_plan
from src.agents.schemas import ScenePlan, ScenePlanItem, SceneResult


_console = Console()


def _is_clean_render(result: SceneResult) -> bool:
    """Whether the worker produced a presentable mp4.

    Plan-mode refuses to let the operator 'approve' a result that didn't
    pass — for example, the tool-use worker exhausted its budget without
    calling done(), or the rendered video has no audio/zero duration.
    """
    if not result.success:
        return False
    if not result.video_path or not Path(result.video_path).exists():
        return False
    return True


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

PrePlanApproval = Callable[[ScenePlan], Awaitable[ScenePlan]]
RerunFn = Callable[[Optional[str]], Awaitable[SceneResult]]
PostSceneApproval = Callable[[ScenePlanItem, SceneResult, RerunFn], Awaitable[SceneResult]]


def make_callbacks(
    *,
    model: str,
    run_id: str,
    project_root: Path,
    auto_open: bool = True,
    max_rounds: int = 5,
) -> tuple[PrePlanApproval, PostSceneApproval]:
    """Build the (pre_plan_approval, post_scene_approval) pair.

    The callbacks close over `model`, `run_id`, `project_root`, and the user
    preferences (auto_open, max_rounds). They never take additional pipeline
    state — pipeline.run wires everything else through closures.
    """
    reviews_path = project_root / "output" / run_id / "reviews.jsonl"

    async def pre_plan_approval(plan: ScenePlan) -> ScenePlan:
        return await _interactive_plan_approval(
            plan, model=model, reviews_path=reviews_path, max_rounds=max_rounds,
        )

    async def post_scene_approval(item: ScenePlanItem, result: SceneResult,
                                  rerun: RerunFn) -> SceneResult:
        return await _interactive_scene_approval(
            item, result, rerun,
            reviews_path=reviews_path,
            auto_open=auto_open,
            max_rounds=max_rounds,
        )

    return pre_plan_approval, post_scene_approval


# ---------------------------------------------------------------------------
# Plan-approval loop
# ---------------------------------------------------------------------------

async def _interactive_plan_approval(plan: ScenePlan, *, model: str,
                                     reviews_path: Path,
                                     max_rounds: int) -> ScenePlan:
    rounds = 0
    while True:
        _display_plan(plan)
        action = _prompt_action(["a", "c", "q"], default="a",
                                labels={"a": "approve", "c": "comment", "q": "quit"})
        if action == "a":
            _append_review(reviews_path, phase="plan", scene_id=None,
                           action="approve", comment=None)
            return plan
        if action == "q":
            _append_review(reviews_path, phase="plan", scene_id=None,
                           action="quit", comment=None)
            _console.print("[bold red]Aborted by user.[/]")
            raise SystemExit(2)
        # action == "c"
        rounds += 1
        if rounds > max_rounds:
            _console.print(
                f"[yellow]Reached {max_rounds}-round revision cap on the plan; "
                f"keeping current plan and continuing.[/]"
            )
            _append_review(reviews_path, phase="plan", scene_id=None,
                           action="cap_hit", comment=None)
            return plan
        comment = _prompt_comment("Plan feedback")
        if not comment:
            continue
        _append_review(reviews_path, phase="plan", scene_id=None,
                       action="comment", comment=comment)
        _console.print(f"[cyan]Revising plan (round {rounds}/{max_rounds})...[/]")
        try:
            plan = await revise_plan(plan, comment, model=model)
        except Exception as exc:
            _console.print(f"[red]revise_plan failed:[/] {exc!r}")
            _console.print("[yellow]Keeping previous plan; you can comment again or quit.[/]")


# ---------------------------------------------------------------------------
# Scene-approval loop
# ---------------------------------------------------------------------------

async def _interactive_scene_approval(item: ScenePlanItem, result: SceneResult,
                                      rerun: RerunFn, *,
                                      reviews_path: Path,
                                      auto_open: bool,
                                      max_rounds: int) -> SceneResult:
    rounds = 0
    opened_paths: set[str] = set()
    while True:
        _display_scene_result(item, result)
        clean = _is_clean_render(result)
        if (clean and auto_open and result.video_path
                and str(result.video_path) not in opened_paths
                and Path(result.video_path).exists()):
            _maybe_open(Path(result.video_path))
            opened_paths.add(str(result.video_path))

        if clean:
            choices = ["a", "c", "r", "q"]
            default = "a"
            labels = {
                "a": "approve", "c": "comment + re-render",
                "r": "retry without comment", "q": "quit",
            }
        else:
            # Worker failed to produce a clean render. Don't let the operator
            # approve a broken scene — only retry / quit, optionally with a
            # comment to nudge the worker.
            _console.print(
                "[yellow]This scene didn't render cleanly. Approve is disabled "
                "until the worker produces a valid mp4 (audio + non-zero "
                "duration). Retry or quit.[/]"
            )
            choices = ["c", "r", "q"]
            default = "r"
            labels = {
                "c": "comment + re-render",
                "r": "retry", "q": "quit",
            }

        action = _prompt_action(choices, default=default, labels=labels)
        if action == "a":
            _append_review(reviews_path, phase="scene", scene_id=item.id,
                           action="approve", comment=None)
            return result
        if action == "q":
            _append_review(reviews_path, phase="scene", scene_id=item.id,
                           action="quit", comment=None)
            _console.print("[bold red]Aborted by user.[/]")
            raise SystemExit(2)

        rounds += 1
        if rounds > max_rounds:
            _console.print(
                f"[yellow]Reached {max_rounds}-round revision cap on scene "
                f"{item.id}; accepting last result and continuing.[/]"
            )
            _append_review(reviews_path, phase="scene", scene_id=item.id,
                           action="cap_hit", comment=None)
            return result

        if action == "c":
            comment = _prompt_comment(f"Scene {item.id} feedback")
            if not comment:
                continue
            _append_review(reviews_path, phase="scene", scene_id=item.id,
                           action="comment", comment=comment)
            _console.print(
                f"[cyan]Re-rendering scene {item.id} with feedback "
                f"(round {rounds}/{max_rounds})...[/]"
            )
            extra = comment
        else:  # action == "r"
            _append_review(reviews_path, phase="scene", scene_id=item.id,
                           action="retry", comment=None)
            _console.print(
                f"[cyan]Re-rendering scene {item.id} (round {rounds}/{max_rounds})...[/]"
            )
            extra = None

        try:
            result = await rerun(extra)
        except Exception as exc:
            _console.print(f"[red]Re-render failed:[/] {exc!r}")
            _console.print("[yellow]Keeping previous result; you can try again or quit.[/]")


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _display_plan(plan: ScenePlan) -> None:
    _console.print(Panel.fit(
        f"[bold]{plan.title}[/]\n"
        f"topic: {plan.topic}\n"
        f"voice: {plan.voice}   total_target: {plan.total_target_seconds:.0f}s   "
        f"scenes: {len(plan.scenes)}",
        title="ScenePlan",
        border_style="cyan",
    ))
    table = Table(show_lines=True, header_style="bold")
    table.add_column("id", width=4)
    table.add_column("slug", style="green")
    table.add_column("dur", width=5, justify="right")
    table.add_column("description", overflow="fold")
    table.add_column("beats / sub-scenes", overflow="fold")
    for s in plan.scenes:
        if s.complexity == "simple" and s.beats:
            beats_text = "\n".join(
                f"• {b.text[:90]}{'…' if len(b.text) > 90 else ''}"
                for b in s.beats
            )
        elif s.sub_scenes:
            beats_text = "\n".join(
                f"[{sub.id}] {sub.description[:80]}{'…' if len(sub.description) > 80 else ''}"
                for sub in s.sub_scenes
            )
        else:
            beats_text = "(no beats)"
        table.add_row(
            s.id, s.slug, f"{s.target_seconds:.0f}s",
            s.description, beats_text,
        )
    _console.print(table)
    if plan.shared_objects:
        so_table = Table(title="shared_objects", show_lines=False, header_style="bold")
        so_table.add_column("name", style="green")
        so_table.add_column("color")
        so_table.add_column("appears_in")
        so_table.add_column("spec", overflow="fold")
        for o in plan.shared_objects:
            so_table.add_row(o.name, o.color, ",".join(o.appears_in),
                             o.spec[:120] + ("…" if len(o.spec) > 120 else ""))
        _console.print(so_table)


def _display_scene_result(item: ScenePlanItem, result: SceneResult) -> None:
    status_style = "green" if result.success else "red"
    status_text = "OK" if result.success else "FAIL"
    body_lines = [
        f"[bold]Scene {item.id}[/] — {item.slug}  [{status_style}]{status_text}[/]",
        f"description: {item.description}",
        f"target: {item.target_seconds:.1f}s   measured: "
        + (f"{result.duration_seconds:.1f}s" if result.duration_seconds else "(none)"),
        f"attempts: {result.attempts}",
        f"video: {result.video_path or '(none)'}",
    ]
    if result.ending_state:
        body_lines.append(f"[dim]ending_state: {result.ending_state[:200]}"
                          f"{'…' if len(result.ending_state) > 200 else ''}[/]")
    if result.last_error:
        body_lines.append(f"[red]error: {result.last_error[:300]}[/]")
    _console.print(Panel("\n".join(body_lines), border_style=status_style))


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def _prompt_action(choices: list[str], *, default: str,
                   labels: dict[str, str]) -> str:
    """Read one keypress-style choice from the operator.

    Uses typer.prompt; accepts the literal letter or the full label. Returns
    a single lowercase character from `choices`.
    """
    legend = "  ".join(rf"\[{c}]={labels.get(c, c)}" for c in choices)
    _console.print(f"[bold]Choose:[/] {legend}")
    while True:
        raw = typer.prompt(f"action [{default}]", default=default).strip().lower()
        if not raw:
            return default
        if raw in choices:
            return raw
        # Allow typing the full label, e.g. "approve"
        for c in choices:
            if labels.get(c, "").lower().startswith(raw):
                return c
        _console.print(f"[yellow]Unknown choice {raw!r}. Try one of: {choices}[/]")


def _prompt_comment(label: str) -> str:
    raw = typer.prompt(f"{label} (single line; empty to cancel)", default="").strip()
    return raw


# ---------------------------------------------------------------------------
# Persistence + side-effects
# ---------------------------------------------------------------------------

def _append_review(path: Path, **fields) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **fields,
    }
    with path.open("a") as f:
        f.write(json.dumps(payload) + "\n")


def _maybe_open(path: Path) -> None:
    """Best-effort macOS `open <path>`. Silent no-op on other platforms or if
    the binary is missing."""
    if not path.exists():
        return
    if sys.platform == "darwin":
        opener = ["open", str(path)]
    elif sys.platform.startswith("linux"):
        opener = ["xdg-open", str(path)]
    else:
        return
    try:
        subprocess.Popen(opener, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, FileNotFoundError):
        pass
