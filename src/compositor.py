"""Compose rendered Manim video with a narration audio track."""

from __future__ import annotations

from pathlib import Path


def merge_audio_video(video_path: str | Path, audio_path: str | Path,
                      out_path: str | Path) -> Path:
    """Mux an audio track onto a video. Trims to shorter of the two."""
    from moviepy.editor import VideoFileClip, AudioFileClip

    video = VideoFileClip(str(video_path))
    audio = AudioFileClip(str(audio_path))
    duration = min(video.duration, audio.duration)
    final = video.subclip(0, duration).set_audio(audio.subclip(0, duration))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(str(out), codec="libx264", audio_codec="aac")
    return out
