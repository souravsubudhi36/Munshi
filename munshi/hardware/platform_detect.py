"""Detect the hardware platform — Raspberry Pi, Android, or desktop dev."""

from __future__ import annotations

import platform
from enum import Enum


class Platform(Enum):
    RASPBERRY_PI = "raspberry_pi"
    ANDROID = "android"
    DESKTOP = "desktop"


def detect_platform() -> Platform:
    machine = platform.machine().lower()
    system = platform.system().lower()

    if system == "linux" and ("aarch64" in machine or "arm" in machine):
        try:
            with open("/proc/cpuinfo") as f:
                if "raspberry pi" in f.read().lower():
                    return Platform.RASPBERRY_PI
        except OSError:
            pass
        return Platform.RASPBERRY_PI  # Assume Pi on ARM Linux

    if system == "linux" and "android" in platform.version().lower():
        return Platform.ANDROID

    return Platform.DESKTOP


CURRENT_PLATFORM = detect_platform()
IS_RASPBERRY_PI = CURRENT_PLATFORM == Platform.RASPBERRY_PI
