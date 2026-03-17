"""Wake word detection using openWakeWord."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Callable

import numpy as np
from loguru import logger

from munshi.config import settings


class WakeWordDetector:
    """
    Continuously listens for the wake word using openWakeWord.
    Calls on_detected() callback when wake word is detected.
    """

    SAMPLE_RATE = 16000
    CHUNK_DURATION_MS = 80  # openWakeWord processes 80ms chunks
    CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)

    def __init__(self, on_detected: Callable[[], None]) -> None:
        self.on_detected = on_detected
        self._running = False
        self._thread: threading.Thread | None = None
        self._model = None

    def _load_model(self) -> None:
        try:
            from openwakeword.model import Model as OWWModel

            model_path = Path(settings.wake_word_model_path)
            if model_path.exists():
                self._model = OWWModel(
                    wakeword_models=[str(model_path)],
                    inference_framework="onnx",
                )
                logger.info(f"Loaded custom wake word model: {model_path}")
            else:
                # Fall back to built-in "hey_jarvis" as placeholder
                self._model = OWWModel(
                    wakeword_models=["hey_jarvis"],
                    inference_framework="onnx",
                )
                logger.warning(
                    f"Custom wake word model not found at {model_path}. "
                    "Using 'hey_jarvis' placeholder. Run scripts/download_models.py"
                )
        except ImportError:
            logger.error("openWakeWord not installed. Wake word detection disabled.")
            self._model = None

    def _detection_loop(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed. Wake word detection disabled.")
            return

        self._load_model()
        if not self._model:
            return

        logger.info("Wake word detection started — listening for 'Munshi'...")

        with sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=self.CHUNK_SAMPLES,
        ) as stream:
            while self._running:
                audio_chunk, _ = stream.read(self.CHUNK_SAMPLES)
                audio_array = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0

                prediction = self._model.predict(audio_array)
                for model_name, score in prediction.items():
                    if score >= settings.wake_word_sensitivity:
                        logger.info(f"Wake word detected! (score={score:.2f})")
                        self.on_detected()
                        # Brief cooldown to avoid double-triggering
                        import time
                        time.sleep(1.0)
                        break

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
