"""Generate a 3Blue1Brown-style narrated video.

Default: multi-agent pipeline (planner → workers → judge → stitch → QA → patch).
Legacy: `--simple` runs the original single-shot generator.

    python scripts/generate.py "Explain the Fourier transform"
    python scripts/generate.py "..." --quality h --music assets/music/ambient.mp3
    python scripts/generate.py "..." --simple
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import typer
from rich import print

from src.gemini_agent import generate_scene, repair_scene, save_scene
from src.music import add_background_music

app = typer.Typer(add_completion=False)


# ---------------------------------------------------------------------------
# Legacy single-shot path (preserved as --simple)
# ---------------------------------------------------------------------------

def _find_rendered_video(scene_class: str) -> Path | None:
    media_root = ROOT / "media" / "videos"
    if not media_root.exists():
        return None
    candidates = list(media_root.rglob(f"{scene_class}.mp4"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _try_render(path: Path, scene_class: str, quality: str,
                resolution: tuple[int, int] | None = None) -> tuple[bool, str]:
    import os
    cmd = ["manim", f"-q{quality}", "--disable_caching"]
    if resolution is not None:
        cmd.extend(["-r", f"{resolution[0]},{resolution[1]}"])
    cmd.extend([str(path), scene_class])
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{ROOT}{os.pathsep}{existing}" if existing else str(ROOT)
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))
    return proc.returncode == 0, (proc.stdout + "\n" + proc.stderr)


def _run_simple(topic: str, quality: str, model: str, music: Path | None,
                preview: bool, resolution: tuple[int, int] | None = None) -> Path:
    print(f"[bold cyan]\\[simple\\] Generating scene for:[/] {topic}  [dim](model={model})[/]")
    script = generate_scene(topic, model=model)
    path = save_scene(script, out_dir=ROOT / "scenes")
    print(f"[green]Wrote[/] {path.relative_to(ROOT)} — class [bold]{script.scene_class}[/]")

    print(f"[bold]Rendering[/] {script.scene_class} at -q{quality}"
          + (f" -r {resolution[0]},{resolution[1]}" if resolution else ""))
    success, output = _try_render(path, script.scene_class, quality, resolution)

    attempt = 1
    max_repairs = 2
    while not success and attempt <= max_repairs:
        print(f"[yellow]Render failed (attempt {attempt}). Asking Gemini to repair...[/]")
        broken = path.read_text()
        fixed = repair_scene(broken, output[-2000:], model=model)
        path = save_scene(fixed, out_dir=ROOT / "scenes")
        script = fixed
        success, output = _try_render(path, script.scene_class, quality, resolution)
        attempt += 1

    if not success:
        print("[red]Render failed after repair attempts. Last error:[/]")
        print(output[-1500:])
        raise typer.Exit(1)

    rendered = _find_rendered_video(script.scene_class)
    if rendered is None:
        print("[red]Could not locate rendered video.[/]")
        raise typer.Exit(1)
    print(f"[green]Rendered:[/] {rendered}")

    final = rendered
    if music:
        if not music.exists():
            print(f"[red]Music file not found:[/] {music}")
            raise typer.Exit(1)
        out = ROOT / "output" / f"{script.scene_class}_with_music.mp4"
        print(f"[bold cyan]Mixing music[/] {music.name} → {out.relative_to(ROOT)}")
        add_background_music(rendered, music, out)
        final = out

    if preview:
        subprocess.run(["open", str(final)], check=False)
    return final


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@app.command()
def main(
    topic: str = typer.Argument(..., help="What the video should explain"),
    quality: str = typer.Option("l", help="Manim quality: l|m|h|k"),
    preview: bool = typer.Option(True, help="Open the video after rendering"),
    model: str = typer.Option("gemini-2.5-pro", help="Gemini model id"),
    music: Path = typer.Option(None, help="Optional background music file"),
    simple: bool = typer.Option(False, "--simple", help="Use the legacy single-shot generator"),
    scenes: int = typer.Option(0, "--scenes", help="Hint for top-level scene count (0 = let planner decide)"),
    parallelism: int = typer.Option(4, "--parallelism", help="Concurrent scene workers"),
    max_attempts: int = typer.Option(4, "--max-attempts", help="Per-scene retry budget"),
    patch_passes: int = typer.Option(2, "--patch-passes", help="Master QA auto-patch limit"),
    qa: bool = typer.Option(True, "--qa/--no-qa", help="Run master QA pass"),
    judge: bool = typer.Option(True, "--judge/--no-judge", help="Per-scene visual+audio judge"),
    judge_frames: int = typer.Option(8, "--judge-frames", help="Frames sampled per scene for judge"),
    no_decompose: bool = typer.Option(False, "--no-decompose", help="Disable complex-scene splitting"),
    voice: str = typer.Option("", "--voice", help="Override Gemini TTS voice (default from planner)"),
    run_id: str = typer.Option("", "--run-id", help="Override run id (default: timestamp + slug)"),
    aspect_ratio: str = typer.Option(
        "16:9", "--aspect-ratio", "--aspect",
        help="Output aspect ratio: 16:9, 9:16, 1:1, 4:5, etc.",
    ),
    parallel: bool = typer.Option(
        False, "--parallel/--no-parallel",
        help=(
            "Render scenes in parallel (legacy mode, no prior-scene context). "
            "Default is sequential with self-validating tool-use workers."
        ),
    ),
    use_tool_worker: bool = typer.Option(
        True, "--tool-worker/--no-tool-worker",
        help=(
            "Use the Gemini function-calling worker that renders + inspects "
            "its own output before declaring done. Default on."
        ),
    ),
    max_tool_iterations: int = typer.Option(
        8, "--max-tool-iterations",
        help="Hard ceiling on tool calls per scene for the tool-use worker.",
    ),
    plan_mode: bool = typer.Option(
        False, "--plan-mode/--no-plan-mode",
        help=(
            "Human-in-the-loop: review the master's plan and every rendered "
            "scene before continuing. Forces sequential mode."
        ),
    ),
    plan_mode_open: bool = typer.Option(
        True, "--plan-mode-open/--no-plan-mode-open",
        help="In --plan-mode, auto-open each rendered scene with the OS opener.",
    ),
    plan_mode_max_rounds: int = typer.Option(
        5, "--plan-mode-max-rounds",
        help="Cap on revision rounds per plan/scene before auto-accepting.",
    ),
):
    from src.agents.tools import parse_aspect_ratio, resolution_for
    try:
        aspect_tuple = parse_aspect_ratio(aspect_ratio)
    except ValueError as exc:
        print(f"[red]{exc}[/]")
        raise typer.Exit(2)
    resolution = resolution_for(aspect_tuple, quality)
    print(f"[dim]aspect_ratio={aspect_ratio}  resolution={resolution[0]}x{resolution[1]}[/]")

    if simple:
        _run_simple(topic, quality, model, music, preview, resolution=resolution)
        return

    if plan_mode and parallel:
        raise typer.BadParameter(
            "--plan-mode requires sequential mode; remove --parallel.",
            param_hint="--plan-mode",
        )

    pre_plan_cb = None
    post_scene_cb = None
    qa_effective = qa
    if plan_mode:
        from src.agents.plan_mode import make_callbacks
        # Resolve the run_id up front so plan_mode and pipeline use the same
        # output directory for reviews.jsonl and artifacts.
        from datetime import datetime
        import re as _re
        if not run_id:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = _re.sub(r"[^a-zA-Z0-9]+", "_", topic.lower()).strip("_")[:40] or "video"
            run_id = f"{ts}_{slug}"
        pre_plan_cb, post_scene_cb = make_callbacks(
            model=model, run_id=run_id, project_root=ROOT,
            auto_open=plan_mode_open, max_rounds=plan_mode_max_rounds,
        )
        # In plan-mode the operator has already approved every scene; the QA
        # pass would second-guess the operator and re-render silently. Force
        # QA off — there's no useful interactive override here.
        qa_effective = False

    from src.agents.pipeline import run as pipeline_run
    final = asyncio.run(pipeline_run(
        topic,
        quality=quality,
        run_id=run_id or None,
        parallelism=parallelism,
        max_attempts=max_attempts,
        patch_passes=patch_passes,
        qa_enabled=qa_effective,
        judge=judge,
        n_frames=judge_frames,
        allow_decomposition=not no_decompose,
        scene_count_hint=scenes if scenes > 0 else None,
        voice_override=voice or None,
        model=model,
        aspect_ratio=aspect_ratio,
        parallel=parallel,
        use_tool_worker=use_tool_worker,
        max_tool_iterations=max_tool_iterations,
        pre_plan_approval=pre_plan_cb,
        post_scene_approval=post_scene_cb,
    ))

    if music:
        if not music.exists():
            print(f"[red]Music file not found:[/] {music}")
            raise typer.Exit(1)
        with_music = final.parent / "final_with_music.mp4"
        print(f"[bold cyan]Mixing music[/] {music.name} -> {with_music}")
        add_background_music(final, music, with_music)
        final = with_music

    print(f"[bold green]Final video:[/] {final}")
    if preview:
        subprocess.run(["open", str(final)], check=False)


if __name__ == "__main__":
    app()
