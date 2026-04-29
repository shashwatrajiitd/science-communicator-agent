"""Lightweight pipeline-wide logger.

One module-level rich Console; every callsite uses `log(scope, msg)` to emit
a timestamped, scope-tagged line. Tool calls have dedicated helpers that
summarise large fields (code blobs, manim log tails, frame lists) so the
console stream stays scannable even when the model is in a tight render
loop.

Log level is read from the `SCA_LOG_LEVEL` env var on import; defaults to
`info`. Set `SCA_LOG_LEVEL=quiet` to suppress everything.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from rich.console import Console
from rich.markup import escape


_console = Console()
_LEVELS = {"quiet": 0, "warn": 1, "info": 2, "debug": 3}
_level = _LEVELS.get(os.environ.get("SCA_LOG_LEVEL", "info").lower(), 2)


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def set_level(level: str) -> None:
    """Override the log level at runtime."""
    global _level
    _level = _LEVELS.get(level.lower(), _level)


def log(scope: str, msg: str, *, style: str = "cyan", level: str = "info",
        markup: bool = True) -> None:
    """Emit one line: `HH:MM:SS [scope] msg`.

    `msg` may contain rich markup (e.g. `[bold]…[/]`) when `markup=True`. Use
    `markup=False` (or escape via `rich.markup.escape`) for arbitrary user
    text that may contain literal `[...]` substrings.
    """
    if _LEVELS.get(level, 2) > _level:
        return
    safe_scope = escape(scope)
    body = msg if markup else escape(msg)
    _console.print(f"[dim]{_ts()}[/] [{style}]\\[{safe_scope}][/] {body}",
                   soft_wrap=True)


def warn(scope: str, msg: str) -> None:
    log(scope, msg, style="yellow", level="warn", markup=False)


def info(scope: str, msg: str) -> None:
    log(scope, msg, style="cyan", level="info", markup=False)


def debug(scope: str, msg: str) -> None:
    log(scope, msg, style="dim", level="debug", markup=False)


# ---------------------------------------------------------------------------
# Tool-call helpers (used by scene_worker.py around the function-calling loop)
# ---------------------------------------------------------------------------

def log_tool_call(scene_id: str, iteration: int, tool_name: str, args: dict) -> None:
    summary = escape(_summarize_args(tool_name, args))
    log(f"worker:{scene_id}",
        f"iter {iteration} → [bold]{escape(tool_name)}[/]({summary})",
        style="magenta")


def log_tool_response(scene_id: str, iteration: int, tool_name: str, response: dict) -> None:
    summary = escape(_summarize_response(tool_name, response))
    is_failure = (
        "error" in response
        or response.get("success") is False
        or response.get("accepted") is False
    )
    style = "red" if is_failure else "green"
    log(f"worker:{scene_id}",
        f"iter {iteration} ← [bold]{escape(tool_name)}[/]: {summary}",
        style=style)


def _summarize_args(tool_name: str, args: dict) -> str:
    if tool_name == "render_manim":
        code = str(args.get("code") or "")
        return f"scene_class={args.get('scene_class')!r}, code={len(code)}B"
    if tool_name == "extract_frames":
        return f"video_path={_short(args.get('video_path'))}, n={args.get('n', 4)}"
    if tool_name == "probe_audio":
        return f"video_path={_short(args.get('video_path'))}"
    if tool_name == "compare_to_prior_frame":
        return f"this_frame_path={_short(args.get('this_frame_path'))}"
    if tool_name == "done":
        s = str(args.get("ending_state_summary") or "")
        return f"video_path={_short(args.get('video_path'))}, summary={_truncate(s, 60)!r}"
    return ", ".join(f"{k}={_short(v)}" for k, v in args.items())


def _summarize_response(tool_name: str, resp: dict) -> str:
    if "error" in resp:
        return f"error: {_truncate(resp['error'], 160)}"
    if tool_name == "render_manim":
        if resp.get("success"):
            return (f"OK duration={resp.get('duration_s')}s "
                    f"video={_short(resp.get('video_path'))}")
        tail = resp.get("log_tail", "") or ""
        return f"FAILED log_tail=…{_truncate(tail.replace(chr(10), ' '), 200)}"
    if tool_name == "extract_frames":
        n = len(resp.get("frames", []))
        return f"{n} frames"
    if tool_name == "probe_audio":
        return f"has_audio={resp.get('has_audio')} duration={resp.get('duration_s')}s"
    if tool_name == "compare_to_prior_frame":
        return f"diff={_truncate(resp.get('diff_summary', ''), 160)!r}"
    if tool_name == "done":
        if resp.get("accepted"):
            return f"ACCEPTED duration={resp.get('duration_s')}s"
        return f"REJECTED: {_truncate(resp.get('error', ''), 160)}"
    return _truncate(str(resp), 200)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _short(p: Any) -> str:
    if p is None:
        return "None"
    s = str(p)
    return s if len(s) <= 60 else f"…{s[-58:]}"


def _truncate(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 1] + "…"
