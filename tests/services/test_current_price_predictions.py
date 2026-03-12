from __future__ import annotations

from pathlib import Path

from pricing_prediction.errors import ServiceUnavailableError
from pricing_prediction.schemas.prediction import PredictCurrentPriceRequest
from pricing_prediction.services.current_price_predictions import CurrentPricePredictionService


def test_prediction_service_returns_prediction_and_warnings(
    app,
    current_price_model_dir: Path,
) -> None:
    app.config["CURRENT_PRICE_MODEL_DIR"] = current_price_model_dir
    app.extensions.pop("current_price_prediction_service", None)

    with app.app_context():
        service = CurrentPricePredictionService.from_app(app)
        prediction = service.predict(
            PredictCurrentPriceRequest(
                query="ropa mujer",
                page_number=1,
                position=4,
                title="Polera mujer sport essentials",
                rating=4.2,
                review_count=12,
            )
        )

        assert prediction.predicted_current_price > 0
        assert prediction.model_name == "cb_leakfree_title_tfidf_deeper"
        assert prediction.model_version == "test-fixture-v1"
        assert prediction.target == "current_price"
        assert prediction.warnings


def test_prediction_service_caches_loaded_bundle(app, current_price_model_dir: Path) -> None:
    app.config["CURRENT_PRICE_MODEL_DIR"] = current_price_model_dir
    app.extensions.pop("current_price_prediction_service", None)

    with app.app_context():
        first = CurrentPricePredictionService.from_app(app)
        second = CurrentPricePredictionService.from_app(app)

        assert first is second


def test_prediction_service_raises_when_bundle_is_missing(app, tmp_path: Path) -> None:
    app.config["CURRENT_PRICE_MODEL_DIR"] = tmp_path / "missing-model"
    app.extensions.pop("current_price_prediction_service", None)

    with app.app_context():
        try:
            CurrentPricePredictionService.from_app(app)
        except ServiceUnavailableError as exc:
            assert "artifact bundle is incomplete" in str(exc)
        else:
            raise AssertionError("Expected a ServiceUnavailableError for a missing model bundle.")
