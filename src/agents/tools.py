"""Pure-Python tools used by the multi-agent pipeline.

These are simple, deterministic functions: subprocess wrappers around `manim`,
`ffmpeg`, and `ffprobe`. They are usable both directly from Python orchestration
code and as ADK function tools (which expect plain typed callables).

No LLM logic in this file.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Manim render
# ---------------------------------------------------------------------------

QUALITY_DIRS = {
    "l": "480p15",
    "m": "720p30",
    "h": "1080p60",
    "k": "2160p60",
}


@dataclass
class RenderResult:
    success: bool
    log: str
    video_path: Optional[Path]


def render_manim_scene(scene_file: Path, scene_class: str, quality: str = "l",
                       extra_args: Optional[list[str]] = None,
                       project_root: Optional[Path] = None) -> RenderResult:
    """Render one Manim Scene class to mp4. Returns the path on success.

    Caching is disabled so re-renders pick up code changes. The scene's
    output lands at media/videos/<scene-stem>/<quality-dir>/<class>.mp4.

    The render subprocess is given a PYTHONPATH that includes the project
    root, so generated scenes can `from src.agents.tts import GeminiTTSService`.
    """
    scene_file = Path(scene_file)
    if project_root is None:
        project_root = _infer_project_root(scene_file)

    cmd = ["manim", f"-q{quality}", "--disable_caching", str(scene_file), scene_class]
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{existing}" if existing else str(project_root)

    # cwd=project_root so the manim media/ dir lands in the project, not in
    # whatever directory the caller happened to be in.
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          env=env, cwd=str(project_root))
    log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    if proc.returncode != 0:
        return RenderResult(success=False, log=log, video_path=None)

    quality_dir = QUALITY_DIRS.get(quality, "480p15")
    expected = project_root / "media" / "videos" / scene_file.stem / quality_dir / f"{scene_class}.mp4"
    if not expected.exists():
        media_videos = project_root / "media" / "videos"
        if media_videos.exists():
            matches = list(media_videos.rglob(f"{scene_class}.mp4"))
            if matches:
                expected = max(matches, key=lambda p: p.stat().st_mtime)
            else:
                return RenderResult(
                    success=False,
                    log=log + f"\n[render_manim_scene] could not locate {scene_class}.mp4",
                    video_path=None,
                )
        else:
            return RenderResult(
                success=False,
                log=log + f"\n[render_manim_scene] media/videos/ does not exist under {project_root}",
                video_path=None,
            )

    return RenderResult(success=True, log=log, video_path=expected)


def _infer_project_root(scene_file: Path) -> Path:
    """Walk up from scene_file until a directory containing pyproject.toml or
    requirements.txt is found. Default to the file's grandparent if not."""
    p = scene_file.resolve()
    for ancestor in [p, *p.parents]:
        if (ancestor / "requirements.txt").exists() or (ancestor / "pyproject.toml").exists():
            return ancestor
    return scene_file.resolve().parent.parent


# ---------------------------------------------------------------------------
# ffprobe / ffmpeg
# ---------------------------------------------------------------------------

@dataclass
class VideoInfo:
    duration: float
    has_audio: bool
    width: int
    height: int


def probe_video(video_path: Path) -> VideoInfo:
    """Return basic info via ffprobe."""
    video_path = Path(video_path)
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=codec_type,width,height",
            "-of", "json",
            str(video_path),
        ],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(proc.stdout)
    duration = float(data.get("format", {}).get("duration", 0.0))
    streams = data.get("streams", [])
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    w = int(video_streams[0]["width"]) if video_streams else 0
    h = int(video_streams[0]["height"]) if video_streams else 0
    return VideoInfo(duration=duration, has_audio=has_audio, width=w, height=h)


def extract_frames(video_path: Path, n: int, out_dir: Path) -> list[Path]:
    """Extract n evenly-spaced frames as PNGs. Returns ordered list of paths."""
    video_path = Path(video_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    duration = probe_video(video_path).duration
    if duration <= 0 or n <= 0:
        return []
    # Sample at the midpoint of each of n equal slices to avoid edges.
    timestamps = [(i + 0.5) * duration / n for i in range(n)]
    frames: list[Path] = []
    for i, t in enumerate(timestamps):
        out = out_dir / f"frame_{i:02d}.png"
        proc = subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video_path),
             "-frames:v", "1", "-q:v", "2", str(out)],
            capture_output=True, text=True,
        )
        if proc.returncode == 0 and out.exists():
            frames.append(out)
    return frames


def extract_audio(video_path: Path, out_path: Path) -> Path:
    """Extract the audio track to a wav file."""
    video_path = Path(video_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-acodec", "pcm_s16le",
         "-ar", "16000", "-ac", "1", str(out_path)],
        capture_output=True, text=True, check=True,
    )
    return out_path


def concat_mp4s(paths: list[Path], out_path: Path) -> Path:
    """Concatenate mp4s with ffmpeg concat demuxer. Tries -c copy first; falls
    back to a re-encode if codecs drift.
    """
    paths = [Path(p) for p in paths]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    list_file = out_path.parent / f".{out_path.stem}_concat.txt"
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in paths))

    # First attempt: copy codecs.
    proc = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
         "-c", "copy", str(out_path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
        # Fallback: re-encode.
        proc = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
             "-c:v", "libx264", "-preset", "fast", "-crf", "20",
             "-c:a", "aac", "-b:a", "192k",
             str(out_path)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {proc.stderr[-2000:]}")
    list_file.unlink(missing_ok=True)
    return out_path


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def copy_to(src: Path, dst: Path) -> Path:
    src = Path(src); dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst
