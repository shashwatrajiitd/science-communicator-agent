"""Mix a background music track under an existing narrated video.

The narration is preserved at full volume; the music is ducked down so it
doesn't fight the voice. Output is a new mp4.
"""

from __future__ import annotations

from pathlib import Path


def add_background_music(
    video_path: str | Path,
    music_path: str | Path,
    out_path: str | Path,
    music_db: float = -22.0,
    fade_in: float = 1.5,
    fade_out: float = 2.0,
) -> Path:
    """Mux a quiet music bed under the existing audio of `video_path`.

    `music_db` is the music volume in dB relative to original (negative = quieter).
    Music is looped if shorter than the video, trimmed if longer.
    """
    import subprocess

    video_path = Path(video_path)
    music_path = Path(music_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Use ffmpeg directly — fastest and most reliable.
    # -stream_loop -1 loops the music; -shortest stops at video length.
    filter_complex = (
        f"[1:a]volume={music_db}dB,"
        f"afade=t=in:st=0:d={fade_in},"
        f"apad[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0,"
        f"afade=t=out:st=END_PLACEHOLDER:d={fade_out}[aout]"
    )

    # We need video duration to set the fade-out start time.
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True, check=True,
    )
    duration = float(probe.stdout.strip())
    fade_out_start = max(0.0, duration - fade_out)
    filter_complex = filter_complex.replace("END_PLACEHOLDER", f"{fade_out_start}")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-stream_loop", "-1", "-i", str(music_path),
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return out_path
