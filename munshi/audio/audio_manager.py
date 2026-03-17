"""AudioManager — coordinates the complete voice pipeline."""

from __future__ import annotations

import asyncio
from enum import Enum, auto

from loguru import logger

from munshi.audio.stt import STTEngine
from munshi.audio.tts import TTSEngine
from munshi.audio.vad import VADCapture
from munshi.audio.wake_word import WakeWordDetector


class AudioState(Enum):
    IDLE = auto()
    LISTENING = auto()
    TRANSCRIBING = auto()
    SPEAKING = auto()


class AudioManager:
    """
    Manages the full voice I/O pipeline:
    1. Wake word detection (background thread)
    2. VAD audio capture
    3. STT transcription
    4. TTS playback
    Emits transcripts via asyncio.Queue for the orchestrator to consume.
    """

    def __init__(self) -> None:
        self.state = AudioState.IDLE
        self._transcript_queue: asyncio.Queue[str] = asyncio.Queue()
        self._wake_detected_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None

        self.stt = STTEngine()
        self.tts = TTSEngine()
        self.vad = VADCapture()
        self._wake_detector = WakeWordDetector(on_detected=self._on_wake_word)

    def _on_wake_word(self) -> None:
        """Called from background thread when wake word is detected."""
        if self._loop and self.state == AudioState.IDLE:
            self._loop.call_soon_threadsafe(self._wake_detected_event.set)

    async def start(self) -> None:
        """Start background wake word detection."""
        self._loop = asyncio.get_event_loop()
        self._wake_detector.start()
        logger.info("AudioManager started — say 'Munshi' to activate.")

    async def stop(self) -> None:
        """Stop all audio processing."""
        self._wake_detector.stop()

    async def listen_and_transcribe(self) -> str:
        """
        Wait for wake word, capture utterance, and return transcript.
        This is the main interface for the orchestrator.
        """
        # Wait for wake word
        self._wake_detected_event.clear()
        self.state = AudioState.IDLE
        await self._wake_detected_event.wait()

        self.state = AudioState.LISTENING
        await self.play_listening_chime()

        # Capture utterance in thread executor (blocking I/O)
        loop = asyncio.get_event_loop()
        audio_bytes = await loop.run_in_executor(None, self.vad.capture)

        self.state = AudioState.TRANSCRIBING
        transcript = await self.stt.transcribe_async(audio_bytes)

        self.state = AudioState.IDLE
        return transcript.strip()

    async def speak(self, text: str) -> None:
        """Speak a response and block until done."""
        if not text:
            return
        self.state = AudioState.SPEAKING
        logger.info(f"Speaking: '{text}'")
        await self.tts.speak_async(text)
        self.state = AudioState.IDLE

    async def play_listening_chime(self) -> None:
        """Play a short audio cue to signal the device is listening."""
        try:
            import numpy as np
            import sounddevice as sd

            # Generate a simple 440Hz beep for 150ms
            sample_rate = 16000
            duration = 0.15
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            tone = (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.float32)
            sd.play(tone, samplerate=sample_rate)
            sd.wait()
        except Exception:
            pass  # Chime is non-critical
