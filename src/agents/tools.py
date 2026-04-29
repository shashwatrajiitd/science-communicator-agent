"""Pure-Python tools used by the multi-agent pipeline.

These are simple, deterministic functions: subprocess wrappers around `manim`,
`ffmpeg`, and `ffprobe`. They are usable both directly from Python orchestration
code and as ADK function tools (which expect plain typed callables).

No LLM logic in this file.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
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

# Pixels along the SHORT side of the frame for each quality preset. We anchor
# the short side (rather than height) so portrait formats like 9:16 produce
# 1080x1920 at -qh — matching the colloquial meaning of "1080p".
QUALITY_SHORT_SIDE = {"l": 480, "m": 720, "h": 1080, "k": 2160}
QUALITY_FPS = {"l": 15, "m": 30, "h": 60, "k": 60}


def parse_aspect_ratio(spec: str) -> tuple[int, int]:
    """Parse an aspect ratio like '16:9', '9:16', '1:1', '4:5'.

    Accepts ':', 'x', or '/' as the separator. Raises ValueError on
    malformed input or a zero/negative component.
    """
    s = (spec or "").strip().lower()
    parts = re.split(r"[:x/]", s)
    if len(parts) != 2:
        raise ValueError(f"Invalid aspect ratio {spec!r}; expected forms like '16:9'.")
    try:
        a, b = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise ValueError(f"Invalid aspect ratio {spec!r}; non-integer component.") from exc
    if a <= 0 or b <= 0:
        raise ValueError(f"Invalid aspect ratio {spec!r}; components must be positive.")
    return a, b


def resolution_for(aspect: tuple[int, int], quality: str) -> tuple[int, int]:
    """Pixel (width, height) for the given aspect ratio + manim quality preset.

    The short side is anchored at the quality preset's pixel count (480/720/
    1080/2160). The long side is scaled and rounded to an even number so x264
    is happy.
    """
    aw, ah = aspect
    short = QUALITY_SHORT_SIDE.get(quality, 480)
    if aw >= ah:
        # landscape or square: short side is height
        h = short
        w = int(round(short * aw / ah))
    else:
        # portrait: short side is width
        w = short
        h = int(round(short * ah / aw))
    if w % 2: w += 1
    if h % 2: h += 1
    return w, h


@dataclass
class RenderResult:
    success: bool
    log: str
    video_path: Optional[Path]


RENDER_TIMEOUT_SECONDS = 300


def render_manim_scene(scene_file: Path, scene_class: str, quality: str = "l",
                       extra_args: Optional[list[str]] = None,
                       project_root: Optional[Path] = None,
                       resolution: Optional[tuple[int, int]] = None,
                       timeout: float = RENDER_TIMEOUT_SECONDS) -> RenderResult:
    """Render one Manim Scene class to mp4. Returns the path on success.

    Caching is disabled so re-renders pick up code changes. The scene's
    output lands at media/videos/<scene-stem>/<quality-dir>/<class>.mp4.

    The render subprocess is given a PYTHONPATH that includes the project
    root, so generated scenes can `from src.agents.tts import GeminiTTSService`.

    If `resolution=(W, H)` is provided, manim is invoked with `-r W,H` and the
    output directory becomes `<H>p<fps>` instead of the default quality dir.
    """
    scene_file = Path(scene_file)
    if project_root is None:
        project_root = _infer_project_root(scene_file)

    cmd = ["manim", f"-q{quality}", "--disable_caching"]
    if resolution is not None:
        w, h = resolution
        cmd.extend(["-r", f"{w},{h}"])
    cmd.extend([str(scene_file), scene_class])
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{existing}" if existing else str(project_root)
    # Manim shells out to `latex`/`dvisvgm` for MathTex/Tex objects. If the
    # user's interactive PATH doesn't include the TeX install, the manim
    # subprocess will see FileNotFoundError. Detect TeX once and prepend.
    env["PATH"] = _augment_path_with_tex(env.get("PATH", ""))

    # cwd=project_root so the manim media/ dir lands in the project, not in
    # whatever directory the caller happened to be in.
    # timeout guards against manim hanging in interpreter shutdown (the
    # manim-voiceover Gemini-TTS adapter has been observed leaving a
    # non-daemon thread alive that blocks Py_FinalizeEx). Popen + communicate
    # so we can SIGKILL the whole process group on timeout.
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env=env, cwd=str(project_root), start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        log = (stdout or "") + ("\n" + stderr if stderr else "")
        return RenderResult(
            success=False,
            log=log + f"\n[render_manim_scene] TIMEOUT after {timeout:.0f}s — child killed",
            video_path=None,
        )
    log = (stdout or "") + ("\n" + stderr if stderr else "")
    if proc.returncode != 0:
        return RenderResult(success=False, log=log, video_path=None)

    if resolution is not None:
        quality_dir = f"{resolution[1]}p{QUALITY_FPS.get(quality, 15)}"
    else:
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


_TEX_PATH_CANDIDATES = [
    "/Library/TeX/texbin",
    "/usr/local/texlive/2026/bin/universal-darwin",
    "/usr/local/texlive/2025/bin/universal-darwin",
    "/usr/local/texlive/2024/bin/universal-darwin",
    "/usr/local/texlive/2023/bin/universal-darwin",
    "/opt/homebrew/bin",
    "/usr/local/bin",
]


def _augment_path_with_tex(current_path: str) -> str:
    """Return PATH with a TeX bin directory prepended, if one exists.

    Manim shells out to `latex`/`dvisvgm` for MathTex/Tex; if those binaries
    aren't on PATH the subprocess fails with FileNotFoundError. The user's
    interactive shell PATH (~/.zshrc etc.) is not always inherited by
    subprocess invocations — most often the case when the parent Python
    was launched from a desktop app or a bare login shell. We fall back to
    a small list of well-known install locations on macOS.
    """
    if shutil.which("latex"):
        return current_path  # already discoverable
    parts = current_path.split(os.pathsep) if current_path else []
    for candidate in _TEX_PATH_CANDIDATES:
        if candidate in parts:
            continue
        latex_bin = Path(candidate) / "latex"
        if latex_bin.exists():
            parts.insert(0, candidate)
            return os.pathsep.join(parts)
    return current_path


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


def extract_last_frame(video_path: Path, out_path: Path) -> Path:
    """Extract the final frame of a video as a PNG.

    Used by the sequential pipeline to hand the prior scene's last frame to
    the next scene's worker. We seek from end-of-file to grab whatever frame
    is closest to the actual final visual frame; the exact offset varies
    because manim sometimes appends silent audio without extending the video
    track.
    """
    video_path = Path(video_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Try -sseof first (seek relative to end). Falls back to absolute seek
    # at duration - 0.3s, then to a middle-frame snapshot if both fail.
    attempts = [
        ["-sseof", "-0.5"],
    ]
    duration = probe_video(video_path).duration
    if duration > 0.3:
        attempts.append(["-ss", f"{duration - 0.3:.3f}"])
    if duration > 0:
        attempts.append(["-ss", f"{duration / 2:.3f}"])

    last_err = ""
    for seek_args in attempts:
        proc = subprocess.run(
            ["ffmpeg", "-y", *seek_args, "-i", str(video_path),
             "-frames:v", "1", "-q:v", "2", str(out_path)],
            capture_output=True, text=True,
        )
        if proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
            return out_path
        last_err = (proc.stderr or "")[-500:]
    raise RuntimeError(f"extract_last_frame failed: {last_err}")


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
