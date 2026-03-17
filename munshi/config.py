"""Centralised configuration via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Anthropic / Claude
    anthropic_api_key: str = ""
    claude_model: str = "claude-haiku-4-5-20251001"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/db/munshi.db"

    # Audio
    wake_word_sensitivity: float = 0.5
    vad_aggressiveness: int = 2

    # Sarvam AI (STT + TTS)
    sarvam_api_key: str = ""
    sarvam_stt_model: str = "saarika:v2"
    sarvam_tts_model: str = "bulbul:v1"
    # BCP-47 language code: hi-IN, bn-IN, ta-IN, te-IN, kn-IN, ml-IN, gu-IN, mr-IN, pa-IN, en-IN
    sarvam_language_code: str = "hi-IN"
    # TTS speaker voice — see Sarvam docs for full list
    sarvam_tts_speaker: str = "meera"

    # Shop
    shop_name: str = "My Shop"
    owner_name: str = "Shop Owner"
    shop_language: str = "hi"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "change_this_secret"

    # Cloud Sync
    supabase_url: str = ""
    supabase_key: str = ""

    # Hardware
    platform: str = "auto"
    led_gpio_pin: int = 18
    led_count: int = 8

    # Paths
    models_dir: str = "./data/models"
    wake_word_model_path: str = "./data/models/wake_word/munshi.onnx"

    @property
    def sarvam_enabled(self) -> bool:
        return bool(self.sarvam_api_key)

    @property
    def cloud_sync_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def db_path(self) -> Path:
        """Absolute path to the SQLite database file."""
        raw = self.database_url.replace("sqlite+aiosqlite:///", "")
        return Path(raw).resolve()


settings = Settings()
