"""
Central configuration loader.

Reads all environment variables (from .env or the shell), validates that
required keys are present, and exposes typed constants for the rest of the
codebase. Import this module early — it raises ConfigurationError fast if
the environment is not set up correctly.

Usage:
    from config.settings import settings
    print(settings.ANTHROPIC_API_KEY)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (parent of the config/ directory)
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class ConfigurationError(Exception):
    """Raised when a required environment variable is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    # ── Companies House ───────────────────────────────────────────────────────
    COMPANIES_HOUSE_API_KEY: str

    # ── Anthropic / Claude ────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str

    # ── Gmail ─────────────────────────────────────────────────────────────────
    GMAIL_CREDENTIALS_PATH: Path
    GMAIL_TOKEN_PATH: Path
    GMAIL_SENDER_ADDRESS: str

    # ── Google Maps (optional) ────────────────────────────────────────────────
    GOOGLE_MAPS_API_KEY: str  # empty string means geocoding is disabled

    # ── Search settings ───────────────────────────────────────────────────────
    MAX_DISTANCE_KM: float
    MAX_COMPANIES_PER_RUN: int  # 0 = no limit

    # ── File paths ────────────────────────────────────────────────────────────
    BASE_CV_PATH: Path
    DB_PATH: Path
    PROJECT_ROOT: Path = field(default_factory=lambda: _PROJECT_ROOT)


def _require(name: str) -> str:
    """Return env var value or raise ConfigurationError."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Required environment variable '{name}' is not set. "
            "Copy .env.example to .env and fill in your values."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _load_settings() -> Settings:
    return Settings(
        COMPANIES_HOUSE_API_KEY=_require("COMPANIES_HOUSE_API_KEY"),
        ANTHROPIC_API_KEY=_require("ANTHROPIC_API_KEY"),
        GMAIL_CREDENTIALS_PATH=Path(_require("GMAIL_CREDENTIALS_PATH")),
        GMAIL_TOKEN_PATH=Path(_optional("GMAIL_TOKEN_PATH", "token.json")),
        GMAIL_SENDER_ADDRESS=_require("GMAIL_SENDER_ADDRESS"),
        GOOGLE_MAPS_API_KEY=_optional("GOOGLE_MAPS_API_KEY"),
        MAX_DISTANCE_KM=float(_optional("MAX_DISTANCE_KM", "80")),
        MAX_COMPANIES_PER_RUN=int(_optional("MAX_COMPANIES_PER_RUN", "20")),
        BASE_CV_PATH=Path(_optional("BASE_CV_PATH", "data/cv_base.md")),
        DB_PATH=Path(_optional("DB_PATH", "data/internship_tracker.db")),
    )


def load_settings() -> Settings:
    """
    Load and validate settings from environment.

    Call this explicitly at application startup (e.g., in scripts/run_pipeline.py).
    Tests that mock Settings never need to call this.

    Returns:
        Validated Settings instance.

    Raises:
        ConfigurationError: If a required environment variable is missing.
    """
    return _load_settings()
