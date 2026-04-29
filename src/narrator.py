"""Narration helpers — generate audio voiceovers for scenes.

Three backends, in order of preference:
  - edge-tts   (free, high quality, async)
  - gtts       (free, simpler)
  - elevenlabs (paid, best quality)
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path


async def _edge_tts(text: str, out_path: Path, voice: str = "en-US-AriaNeural") -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def narrate_edge(text: str, out_path: str | Path, voice: str = "en-US-AriaNeural") -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_edge_tts(text, out, voice))
    return out


def narrate_gtts(text: str, out_path: str | Path, lang: str = "en") -> Path:
    from gtts import gTTS

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    gTTS(text=text, lang=lang).save(str(out))
    return out


def narrate_elevenlabs(text: str, out_path: str | Path, voice_id: str = "Rachel") -> Path:
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    audio = client.text_to_speech.convert(voice_id=voice_id, text=text)
    with open(out, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return out
