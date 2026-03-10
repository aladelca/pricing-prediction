from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from flask import Flask, jsonify
from pydantic import ValidationError

from pricing_prediction.api import api_v1
from pricing_prediction.api.health import health_bp
from pricing_prediction.config import Config, ensure_runtime_directories
from pricing_prediction.errors import ApiError
from pricing_prediction.extensions import db


def create_app(config_overrides: dict[str, Any] | None = None) -> Flask:
    ensure_runtime_directories()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if config_overrides:
        app.config.from_mapping(config_overrides)

    db.init_app(app)

    app.extensions["scrape_executor"] = ThreadPoolExecutor(
        max_workers=app.config["SCRAPER_EXECUTOR_WORKERS"]
    )

    app.register_blueprint(health_bp)
    app.register_blueprint(api_v1)
    register_error_handlers(app)
    return app


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> tuple[dict[str, Any], int]:
        return {"error": {"message": error.message}}, error.status_code

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> tuple[dict[str, Any], int]:
        return {"error": {"message": "Validation failed", "details": error.errors()}}, 422

    @app.errorhandler(404)
    def handle_not_found(_: Any) -> tuple[dict[str, Any], int]:
        return {"error": {"message": "Resource not found"}}, 404

    @app.errorhandler(500)
    def handle_internal_error(_: Any) -> tuple[dict[str, Any], int]:
        return {"error": {"message": "Internal server error"}}, 500

    @app.get("/")
    def root() -> Any:
        return jsonify({"service": "pricing-prediction", "status": "ok"})
