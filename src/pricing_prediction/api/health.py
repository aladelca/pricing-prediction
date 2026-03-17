from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify

from pricing_prediction.errors import ServiceUnavailableError
from pricing_prediction.services.current_price_predictions import CurrentPricePredictionService

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def healthcheck() -> tuple[Any, int]:
    return jsonify({"status": "ok", "service": "pricing-prediction"}), 200


@health_bp.get("/ready")
def readiness_check() -> tuple[Any, int]:
    try:
        service = CurrentPricePredictionService.from_app(current_app)
    except ServiceUnavailableError as exc:
        return jsonify({"error": {"message": str(exc)}}), 503

    return (
        jsonify(
            {
                "status": "ready",
                "service": "pricing-prediction",
                "model_name": service.bundle.metadata.model_name,
                "model_version": service.bundle.metadata.model_version,
            }
        ),
        200,
    )
