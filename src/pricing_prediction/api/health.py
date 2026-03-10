from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def healthcheck() -> tuple[Any, int]:
    return jsonify({"status": "ok", "service": "pricing-prediction"}), 200
