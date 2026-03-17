from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any


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


def _split_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    items = tuple(part.strip().lower() for part in value.split(",") if part.strip())
    return items or default


def _as_path(value: str | Path) -> Path:
    if isinstance(value, Path):
        return value
    return Path(value)


def _as_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _runtime_mode(value: str | None) -> str:
    mode = (value or "full").strip().lower()
    if mode not in {"full", "inference"}:
        raise ValueError("APP_RUNTIME_MODE must be 'full' or 'inference'.")
    return mode


def _model_source(value: str | None) -> str:
    source = (value or "local").strip().lower()
    if source not in {"local", "s3"}:
        raise ValueError("MODEL_SOURCE must be 'local' or 's3'.")
    return source


def _sqlite_path_from_uri(uri: str) -> Path | None:
    if uri == "sqlite:///:memory:":
        return None
    prefix = "sqlite:///"
    if not uri.startswith(prefix):
        return None
    return Path(uri.removeprefix(prefix))


class Config:
    BASE_DIR = Path(__file__).resolve().parents[2]
    DEFAULT_SQLITE_PATH = BASE_DIR / "instance" / "pricing_prediction.db"
    DEFAULT_CURRENT_PRICE_MODEL_DIR = BASE_DIR / "instance" / "models" / "current_price" / "dev"
    DEFAULT_CURRENT_PRICE_MODEL_CACHE_DIR = Path("/tmp/pricing-prediction/models/current_price")

    TESTING = False
    APP_RUNTIME_MODE = "full"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DEFAULT_SQLITE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MODEL_SOURCE = "local"
    CURRENT_PRICE_MODEL_DIR = DEFAULT_CURRENT_PRICE_MODEL_DIR
    CURRENT_PRICE_MODEL_CACHE_DIR = DEFAULT_CURRENT_PRICE_MODEL_CACHE_DIR
    CURRENT_PRICE_MODEL_S3_BUCKET: str | None = None
    CURRENT_PRICE_MODEL_S3_PREFIX: str | None = None
    CURRENT_PRICE_MODEL_S3_VERSION: str | None = None
    CURRENT_PRICE_MODEL_S3_MANIFEST_KEY: str | None = None
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(8 * 1024 * 1024)))
    WEB_PREDICTION_MAX_IMAGE_FILES = int(os.getenv("WEB_PREDICTION_MAX_IMAGE_FILES", "6"))
    WEB_PREDICTION_ALLOWED_EXTENSIONS = _split_csv(
        os.getenv("WEB_PREDICTION_ALLOWED_EXTENSIONS"),
        ("jpg", "jpeg", "png", "webp"),
    )

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


def load_runtime_config() -> dict[str, Any]:
    return {
        "APP_RUNTIME_MODE": _runtime_mode(os.getenv("APP_RUNTIME_MODE")),
        "SQLALCHEMY_DATABASE_URI": _normalize_database_url(
            os.getenv("DATABASE_URL", f"sqlite:///{Config.DEFAULT_SQLITE_PATH}")
        ),
        "CURRENT_PRICE_MODEL_DIR": _as_path(
            os.getenv("CURRENT_PRICE_MODEL_DIR", str(Config.DEFAULT_CURRENT_PRICE_MODEL_DIR))
        ),
        "MODEL_SOURCE": _model_source(os.getenv("MODEL_SOURCE")),
        "CURRENT_PRICE_MODEL_CACHE_DIR": _as_path(
            os.getenv(
                "CURRENT_PRICE_MODEL_CACHE_DIR",
                str(Config.DEFAULT_CURRENT_PRICE_MODEL_CACHE_DIR),
            )
        ),
        "CURRENT_PRICE_MODEL_S3_BUCKET": _as_optional_string(
            os.getenv("CURRENT_PRICE_MODEL_S3_BUCKET")
        ),
        "CURRENT_PRICE_MODEL_S3_PREFIX": _as_optional_string(
            os.getenv("CURRENT_PRICE_MODEL_S3_PREFIX")
        ),
        "CURRENT_PRICE_MODEL_S3_VERSION": _as_optional_string(
            os.getenv("CURRENT_PRICE_MODEL_S3_VERSION")
        ),
        "CURRENT_PRICE_MODEL_S3_MANIFEST_KEY": _as_optional_string(
            os.getenv("CURRENT_PRICE_MODEL_S3_MANIFEST_KEY")
        ),
    }


def ensure_runtime_directories(config: Mapping[str, Any]) -> None:
    sqlite_path = _sqlite_path_from_uri(str(config["SQLALCHEMY_DATABASE_URI"]))
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    current_price_model_dir = _as_path(config["CURRENT_PRICE_MODEL_DIR"])
    current_price_model_dir.parent.mkdir(parents=True, exist_ok=True)

    current_price_model_cache_dir = _as_path(config["CURRENT_PRICE_MODEL_CACHE_DIR"])
    current_price_model_cache_dir.mkdir(parents=True, exist_ok=True)
