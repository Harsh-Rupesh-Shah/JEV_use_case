"""Configuration settings for The Retirement Whisperer."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from root project directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application and decision engine settings."""

    # API Keys
    LAYA_IMPOSSIBLE_API_KEY: str = os.getenv("LAYA_IMPOSSIBLE_API_KEY", "")
    TYPESAFE_API_KEY: str = os.getenv("TYPESAFE_API_KEY", "")
    
    # LLM API Keys (Free Tier)
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_API_KEY_BACKUP: str = os.getenv("GOOGLE_API_KEY_BACKUP", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # LLM Models (100% Free Tiers)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")

    # System One Arbiter Configuration
    JEV_BASE_URL: str = os.getenv("JEV_BASE_URL", "https://api.impossibl.com")
    JEV_MODEL: str = os.getenv("JEV_MODEL", "convaiinnovations/laya")

    # Arbiter Request Configuration
    REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15.0"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # Decision Thresholds
    FIDELITY_MIN_THRESHOLD: float = float(os.getenv("FIDELITY_MIN_THRESHOLD", "0.75"))
    ESCALATION_TRIGGER_THRESHOLD: float = float(os.getenv("ESCALATION_TRIGGER_THRESHOLD", "0.75"))

    # Server Settings
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))

    @classmethod
    def get_arbiter_api_key(cls) -> str:
        """Get the active API key for the System One arbiter."""
        return cls.LAYA_IMPOSSIBLE_API_KEY or cls.TYPESAFE_API_KEY


settings = Settings()
