from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, jsonify, request

from pricing_prediction.schemas.prediction import PredictCurrentPriceRequest
from pricing_prediction.services.current_price_predictions import CurrentPricePredictionService

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.post("/predictions/current-price")
def predict_current_price() -> tuple[Any, int]:
    payload = PredictCurrentPriceRequest.model_validate(request.get_json(silent=True) or {})
    service = CurrentPricePredictionService.from_app(current_app)
    prediction = service.predict(payload)
    return jsonify({"data": prediction.model_dump()}), 200
