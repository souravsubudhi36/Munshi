"""Voice Activity Detection — captures a complete utterance after wake word."""

from __future__ import annotations

import numpy as np
from loguru import logger


class VADCapture:
    """
    Captures audio until end-of-speech is detected using webrtcvad.
    Returns raw PCM bytes at 16kHz mono int16.
    """

    SAMPLE_RATE = 16000
    FRAME_DURATION_MS = 30  # webrtcvad supports 10, 20, or 30ms frames
    FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
    FRAME_BYTES = FRAME_SAMPLES * 2  # int16 = 2 bytes

    SILENCE_THRESHOLD_FRAMES = 27  # ~0.8s of silence triggers end-of-speech
    MAX_DURATION_FRAMES = int(8.0 * 1000 / FRAME_DURATION_MS)  # 8 second max

    def __init__(self, aggressiveness: int = 2) -> None:
        self.aggressiveness = aggressiveness
        self._vad = None

    def _get_vad(self):
        if self._vad is None:
            try:
                import webrtcvad
                self._vad = webrtcvad.Vad(self.aggressiveness)
            except ImportError:
                logger.warning("webrtcvad not installed — using energy-based VAD fallback.")
                self._vad = _EnergyVAD()
        return self._vad

    def capture(self) -> bytes:
        """Block until a complete utterance is captured. Returns raw PCM bytes."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed.")
            return b""

        vad = self._get_vad()
        audio_frames: list[bytes] = []
        silence_count = 0
        total_frames = 0
        speech_started = False

        logger.debug("VAD: listening for speech...")

        with sd.RawInputStream(
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=self.FRAME_SAMPLES,
        ) as stream:
            while True:
                frame_data, _ = stream.read(self.FRAME_SAMPLES)
                frame_bytes = bytes(frame_data)
                total_frames += 1

                is_speech = vad.is_speech(frame_bytes, self.SAMPLE_RATE)

                if is_speech:
                    speech_started = True
                    silence_count = 0
                    audio_frames.append(frame_bytes)
                elif speech_started:
                    silence_count += 1
                    audio_frames.append(frame_bytes)
                    if silence_count >= self.SILENCE_THRESHOLD_FRAMES:
                        logger.debug(f"VAD: end of speech ({len(audio_frames)} frames)")
                        break
                else:
                    # Pre-speech buffer (keep last 0.5s in case speech starts mid-frame)
                    audio_frames = audio_frames[-16:]

                if total_frames >= self.MAX_DURATION_FRAMES:
                    logger.debug("VAD: max duration reached")
                    break

        return b"".join(audio_frames)


class _EnergyVAD:
    """Simple energy-based VAD fallback when webrtcvad is unavailable."""

    ENERGY_THRESHOLD = 300

    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        audio = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
        energy = np.sqrt(np.mean(audio ** 2))
        return energy > self.ENERGY_THRESHOLD
