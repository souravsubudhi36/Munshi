"""WS2812B LED ring controller for visual status feedback.

States:
- IDLE: off (dim blue pulse)
- LISTENING: solid cyan
- PROCESSING: rotating yellow
- SPEAKING: solid green
- ERROR: red flash
"""

from __future__ import annotations

from enum import Enum, auto

from loguru import logger

from munshi.config import settings
from munshi.hardware.platform_detect import IS_RASPBERRY_PI


class LEDState(Enum):
    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()
    ERROR = auto()


class LEDController:
    def __init__(self) -> None:
        self._strip = None
        self._available = False
        if IS_RASPBERRY_PI:
            self._init_strip()

    def _init_strip(self) -> None:
        try:
            from rpi_ws281x import Adafruit_NeoPixel, Color

            self._strip = Adafruit_NeoPixel(
                settings.led_count,
                settings.led_gpio_pin,
                800000,  # LED signal frequency
                5,       # DMA channel
                False,   # Invert signal
                255,     # Brightness
            )
            self._strip.begin()
            self._available = True
            logger.info(f"LED ring initialised: {settings.led_count} LEDs on GPIO {settings.led_gpio_pin}")
        except ImportError:
            logger.debug("rpi_ws281x not available — LED control disabled.")
        except Exception as e:
            logger.warning(f"LED init failed: {e}")

    def set_state(self, state: LEDState) -> None:
        if not self._available or not self._strip:
            return

        from rpi_ws281x import Color

        color_map = {
            LEDState.IDLE: Color(0, 0, 20),          # dim blue
            LEDState.LISTENING: Color(0, 200, 200),   # cyan
            LEDState.PROCESSING: Color(200, 200, 0),  # yellow
            LEDState.SPEAKING: Color(0, 200, 0),      # green
            LEDState.ERROR: Color(200, 0, 0),          # red
        }
        color = color_map.get(state, Color(0, 0, 0))
        for i in range(self._strip.numPixels()):
            self._strip.setPixelColor(i, color)
        self._strip.show()

    def off(self) -> None:
        self.set_state(LEDState.IDLE)
