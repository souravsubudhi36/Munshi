#!/usr/bin/env python3
"""Download required ML models for Munshi.

STT and TTS are handled by Sarvam AI (cloud API — no local models needed).
Only the wake word model needs to be downloaded locally.

Run once during device setup:
    python scripts/download_models.py
"""

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

MODELS_DIR = Path("./data/models")
WAKE_WORD_DIR = MODELS_DIR / "wake_word"

# Official openWakeWord release assets (v0.5.1)
OWW_RELEASES = "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1"
REQUIRED_MODELS = {
    "embedding_model.onnx": f"{OWW_RELEASES}/embedding_model.onnx",
    "melspectrogram.onnx": f"{OWW_RELEASES}/melspectrogram.onnx",
    "hey_jarvis_v0.1.onnx": f"{OWW_RELEASES}/hey_jarvis_v0.1.onnx",
}


def ensure_dirs():
    WAKE_WORD_DIR.mkdir(parents=True, exist_ok=True)
    print("✓ Model directories created.")


def download_file(url: str, dest: Path):
    if dest.exists():
        print(f"  - {dest.name} already exists.")
        return

    print(f"  - Downloading {dest.name}...")
    try:
        urllib.request.urlretrieve(url, dest)
        print(f"    ✓ Done.")
    except Exception as e:
        print(f"    ✗ Failed: {e}")


def setup_wake_word():
    print("\n[1/1] Setting up wake word models...")
    ensure_dirs()

    for name, url in REQUIRED_MODELS.items():
        download_file(url, WAKE_WORD_DIR / name)

    try:
        import openwakeword
        print("\n✓ openWakeWord installed.")
        print("  Default wake word: 'hey_jarvis' (local models downloaded).")
    except ImportError:
        print("\n✗ openWakeWord not installed. Run: poetry install")


def print_summary():
    print("\n" + "=" * 50)
    print("Setup complete! Next steps:")
    print("1. Set ANTHROPIC_API_KEY and SARVAM_API_KEY in .env")
    print("2. Run database migrations: poetry run alembic upgrade head")
    print("3. Start Munshi: poetry run munshi")
    print("=" * 50)


if __name__ == "__main__":
    print("Munshi — Model Setup Script")
    print("=" * 50)
    print("Note: STT and TTS use Sarvam AI cloud API.")
    setup_wake_word()
    print_summary()
