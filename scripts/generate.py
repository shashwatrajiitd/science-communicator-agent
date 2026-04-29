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


def _try_render(path: Path, scene_class: str, quality: str) -> tuple[bool, str]:
    cmd = ["manim", f"-q{quality}", "--disable_caching", str(path), scene_class]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + "\n" + proc.stderr)


def _run_simple(topic: str, quality: str, model: str, music: Path | None,
                preview: bool) -> Path:
    print(f"[bold cyan]\\[simple\\] Generating scene for:[/] {topic}  [dim](model={model})[/]")
    script = generate_scene(topic, model=model)
    path = save_scene(script, out_dir=ROOT / "scenes")
    print(f"[green]Wrote[/] {path.relative_to(ROOT)} — class [bold]{script.scene_class}[/]")

    print(f"[bold]Rendering[/] {script.scene_class} at -q{quality}")
    success, output = _try_render(path, script.scene_class, quality)

    attempt = 1
    max_repairs = 2
    while not success and attempt <= max_repairs:
        print(f"[yellow]Render failed (attempt {attempt}). Asking Gemini to repair...[/]")
        broken = path.read_text()
        fixed = repair_scene(broken, output[-2000:], model=model)
        path = save_scene(fixed, out_dir=ROOT / "scenes")
        script = fixed
        success, output = _try_render(path, script.scene_class, quality)
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
):
    if simple:
        _run_simple(topic, quality, model, music, preview)
        return

    from src.agents.pipeline import run as pipeline_run
    final = asyncio.run(pipeline_run(
        topic,
        quality=quality,
        run_id=run_id or None,
        parallelism=parallelism,
        max_attempts=max_attempts,
        patch_passes=patch_passes,
        qa_enabled=qa,
        judge=judge,
        n_frames=judge_frames,
        allow_decomposition=not no_decompose,
        scene_count_hint=scenes if scenes > 0 else None,
        voice_override=voice or None,
        model=model,
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
