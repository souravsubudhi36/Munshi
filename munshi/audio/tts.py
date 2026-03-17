"""Text-to-Speech using Sarvam AI (bulbul model).

Supports all major Indian languages with natural voices.
API docs: https://docs.sarvam.ai/api-reference-docs/endpoints/text-to-speech

Available speakers (bulbul:v1):
  meera, pavithra, maitreyi, arvind, amol, amartya, diya, neel, (and more)
"""

from __future__ import annotations

import asyncio
import base64
import io
import wave

import httpx
import numpy as np
import sounddevice as sd
from loguru import logger

from munshi.config import settings

_SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

# Sarvam TTS returns 22050 Hz audio
_SARVAM_SAMPLE_RATE = 22050


class TTSEngine:
    """
    Text-to-speech via Sarvam AI (bulbul model).
    Supports 10+ Indian languages with multiple voice options.
    """

    def speak(self, text: str) -> None:
        """Synthesise and play text synchronously."""
        if not text:
            return

        if not settings.sarvam_enabled:
            logger.warning("SARVAM_API_KEY not set — TTS unavailable.")
            return

        audio_bytes = self._synthesise(text)
        if audio_bytes:
            self._play_wav(audio_bytes)

    def _synthesise(self, text: str) -> bytes | None:
        """Call Sarvam TTS API and return WAV bytes."""
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(
                    _SARVAM_TTS_URL,
                    headers={
                        "api-subscription-key": settings.sarvam_api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "inputs": [text],
                        "target_language_code": settings.sarvam_language_code,
                        "speaker": settings.sarvam_tts_speaker,
                        "model": settings.sarvam_tts_model,
                        "enable_preprocessing": True,
                    },
                )
                response.raise_for_status()

            # Response: {"audios": ["<base64-encoded-wav>", ...]}
            audios = response.json().get("audios", [])
            if not audios:
                logger.error("Sarvam TTS returned empty audio list.")
                return None

            return base64.b64decode(audios[0])

        except httpx.HTTPStatusError as e:
            logger.error(f"Sarvam TTS HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except httpx.TimeoutException:
            logger.error("Sarvam TTS request timed out.")
            return None
        except Exception as e:
            logger.error(f"Sarvam TTS error: {e}")
            return None

    def _play_wav(self, wav_bytes: bytes) -> None:
        """Decode WAV bytes and play through the speaker."""
        try:
            buf = io.BytesIO(wav_bytes)
            with wave.open(buf, "rb") as wf:
                sample_rate = wf.getframerate()
                n_channels = wf.getnchannels()
                raw = wf.readframes(wf.getnframes())

            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            if n_channels > 1:
                audio = audio.reshape(-1, n_channels).mean(axis=1)

            sd.play(audio, samplerate=sample_rate)
            sd.wait()
        except Exception as e:
            logger.error(f"TTS playback error: {e}")

    async def speak_async(self, text: str) -> None:
        """Async wrapper — runs the blocking call in a thread executor."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.speak, text)
