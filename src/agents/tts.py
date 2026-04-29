"""Gemini TTS adapter for manim-voiceover.

Subclass of `manim_voiceover.services.base.SpeechService` that synthesises
speech using `gemini-2.5-flash-preview-tts`. Output audio is PCM 16-bit/24 kHz
mono — wrapped in a WAV header and saved to the manim-voiceover cache.

Usage from a Manim scene:

    from manim_voiceover import VoiceoverScene
    from src.agents.tts import GeminiTTSService

    class MyScene(VoiceoverScene):
        def construct(self):
            self.set_speech_service(GeminiTTSService(voice="Aoede"))
            with self.voiceover(text="hello world") as tracker:
                self.play(..., run_time=tracker.duration)
"""

from __future__ import annotations

import io
import os
import wave
from pathlib import Path
from typing import Optional

from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import SpeechService

DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE = "Aoede"

# Sample rate Gemini TTS returns. As of early 2026 this is 24 kHz mono PCM16.
GEMINI_TTS_SAMPLE_RATE = 24000


class GeminiTTSService(SpeechService):
    """SpeechService that calls Gemini's native TTS via google-genai."""

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        model: str = DEFAULT_MODEL,
        style_prompt: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.voice = voice
        self.model = model
        self.style_prompt = style_prompt

    def generate_from_text(
        self,
        text: str,
        cache_dir: Optional[str] = None,
        path: Optional[str] = None,
        **_kwargs,
    ) -> dict:
        if cache_dir is None:
            cache_dir = self.cache_dir
        cache_dir = Path(cache_dir)

        input_text = remove_bookmarks(text)
        input_data = {
            "input_text": input_text,
            "service": "gemini_tts",
            "voice": self.voice,
            "model": self.model,
            "style_prompt": self.style_prompt or "",
        }

        cached = self.get_cached_result(input_data, cache_dir)
        if cached is not None:
            return cached

        # manim-voiceover's get_duration uses mutagen.mp3.MP3 which only
        # supports MP3 — output mp3 here, even though Gemini hands back PCM.
        if path is None:
            audio_filename = self.get_audio_basename(input_data) + ".mp3"
        else:
            audio_filename = path
        audio_path = cache_dir / audio_filename

        # Build the prompt: prepend optional style direction.
        if self.style_prompt:
            prompt = f"{self.style_prompt}\n\n{input_text}"
        else:
            prompt = input_text

        pcm = self._call_gemini_tts(prompt)
        _write_mp3_from_pcm(audio_path, pcm, GEMINI_TTS_SAMPLE_RATE)

        return {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_filename,
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _call_gemini_tts(self, prompt: str) -> bytes:
        from google import genai
        from google.genai import types

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY not set in environment.")

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.voice
                        )
                    )
                ),
            ),
        )
        # Walk the response to extract inline audio bytes.
        for cand in response.candidates or []:
            content = getattr(cand, "content", None)
            if not content:
                continue
            for part in content.parts or []:
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    data = inline.data
                    if isinstance(data, str):  # may arrive base64-encoded
                        import base64
                        data = base64.b64decode(data)
                    return data
        raise RuntimeError("Gemini TTS returned no audio data. "
                           "Verify the model id, billing, and that the prompt is non-empty.")


def _write_mp3_from_pcm(path: Path, pcm_bytes: bytes, sample_rate: int) -> None:
    """Wrap raw PCM 16-bit mono in a WAV header and export as MP3 via pydub."""
    from pydub import AudioSegment

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Build an in-memory WAV, then re-export as MP3.
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    buf.seek(0)

    audio = AudioSegment.from_wav(buf)
    audio.export(str(path), format="mp3", bitrate="128k")
