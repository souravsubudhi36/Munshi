#!/usr/bin/env python3
"""Download required ML models for Munshi.

STT and TTS are handled by Sarvam AI (cloud API — no local models needed).
Only the wake word model needs to be downloaded locally.

Run once during device setup:
    python scripts/download_models.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

MODELS_DIR = Path("./data/models")
WAKE_WORD_DIR = MODELS_DIR / "wake_word"


def ensure_dirs():
    WAKE_WORD_DIR.mkdir(parents=True, exist_ok=True)
    print("✓ Model directories created.")


def setup_wake_word():
    print("\n[1/1] Setting up wake word model...")
    try:
        import openwakeword
        print("✓ openWakeWord installed — built-in models available.")
        print("  Default wake word: 'hey_jarvis' (placeholder).")
        print("  To train a custom 'Munshi' wake word:")
        print("    python scripts/train_wake_word.py")
    except ImportError:
        print("✗ openWakeWord not installed. Run: pip install openwakeword")


def print_summary():
    print("\n" + "=" * 50)
    print("Setup complete! Next steps:")
    print("1. Copy .env.example to .env")
    print("2. Set ANTHROPIC_API_KEY and SARVAM_API_KEY in .env")
    print("3. Run database migrations: alembic upgrade head")
    print("4. Start Munshi: python -m munshi.main")
    print("=" * 50)


if __name__ == "__main__":
    print("Munshi — Model Setup Script")
    print("=" * 50)
    print("Note: STT and TTS use Sarvam AI cloud API — no local models needed.")
    ensure_dirs()
    setup_wake_word()
    print_summary()
