"""Speech-to-Text using Sarvam AI (saarika model).

Supports all major Indian languages via the Sarvam AI API:
  hi-IN, bn-IN, ta-IN, te-IN, kn-IN, ml-IN, gu-IN, mr-IN, pa-IN, en-IN

API docs: https://docs.sarvam.ai/api-reference-docs/endpoints/speech-to-text
"""

from __future__ import annotations

import asyncio
import io
import wave

import httpx
from loguru import logger

from munshi.config import settings

_SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Wrap raw PCM int16 bytes in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


class STTEngine:
    """
    Speech recognition via Sarvam AI (saarika model).
    Supports 10+ Indian languages; auto-detects language from the shop config.
    Falls back to a warning if API key is not configured.
    """

    def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe raw PCM bytes (16kHz, mono, int16) to text.
        Returns empty string on failure.
        """
        if not audio_bytes:
            return ""

        if not settings.sarvam_enabled:
            logger.warning(
                "SARVAM_API_KEY not set — STT unavailable. "
                "Add it to .env to enable speech recognition."
            )
            return ""

        wav_bytes = _pcm_to_wav(audio_bytes)

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(
                    _SARVAM_STT_URL,
                    headers={"api-subscription-key": settings.sarvam_api_key},
                    files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                    data={
                        "model": settings.sarvam_stt_model,
                        "language_code": settings.sarvam_language_code,
                        "with_timestamps": "false",
                    },
                )
                response.raise_for_status()

            transcript = response.json().get("transcript", "").strip()
            logger.debug(f"Sarvam STT: '{transcript}' (lang={settings.sarvam_language_code})")
            return transcript

        except httpx.HTTPStatusError as e:
            logger.error(f"Sarvam STT HTTP error {e.response.status_code}: {e.response.text}")
            return ""
        except httpx.TimeoutException:
            logger.error("Sarvam STT request timed out.")
            return ""
        except Exception as e:
            logger.error(f"Sarvam STT error: {e}")
            return ""

    async def transcribe_async(self, audio_bytes: bytes) -> str:
        """Async wrapper — runs the blocking HTTP call in a thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.transcribe, audio_bytes)
