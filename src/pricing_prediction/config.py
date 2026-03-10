from __future__ import annotations

import os
from pathlib import Path


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_database_url(value: str) -> str:
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://") and "+psycopg" not in value:
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


class Config:
    BASE_DIR = Path(__file__).resolve().parents[2]
    DEFAULT_SQLITE_PATH = BASE_DIR / "instance" / "pricing_prediction.db"

    TESTING = False
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(
        os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SCRAPER_SOURCE = "falabella_pe"
    SCRAPER_DEFAULT_MAX_PAGES = int(os.getenv("SCRAPER_DEFAULT_MAX_PAGES", "30"))
    SCRAPER_MAX_ALLOWED_PAGES = int(os.getenv("SCRAPER_MAX_ALLOWED_PAGES", "30"))
    SCRAPER_REQUEST_TIMEOUT = float(os.getenv("SCRAPER_REQUEST_TIMEOUT", "20"))
    SCRAPER_REQUEST_DELAY_MS = int(os.getenv("SCRAPER_REQUEST_DELAY_MS", "300"))
    SCRAPER_RETRY_ATTEMPTS = int(os.getenv("SCRAPER_RETRY_ATTEMPTS", "3"))
    SCRAPER_USER_AGENT = os.getenv(
        "SCRAPER_USER_AGENT",
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 Safari/537.36"
        ),
    )
    SCRAPER_ENABLE_BROWSER_FALLBACK = _as_bool(os.getenv("SCRAPER_ENABLE_BROWSER_FALLBACK"), True)
    SCRAPER_INLINE_EXECUTION = _as_bool(os.getenv("SCRAPER_INLINE_EXECUTION"), False)
    SCRAPER_EXECUTOR_WORKERS = int(os.getenv("SCRAPER_EXECUTOR_WORKERS", "2"))


def ensure_runtime_directories() -> None:
    Config.DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
