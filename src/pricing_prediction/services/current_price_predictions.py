from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from catboost import Pool
from flask import Flask

from pricing_prediction.errors import ServiceUnavailableError
from pricing_prediction.ml.current_price.artifacts import (
    CurrentPriceArtifactBundle,
    load_current_price_artifacts,
)
from pricing_prediction.ml.current_price.features import (
    build_inference_source_frame,
    transform_title_text,
)
from pricing_prediction.schemas.prediction import (
    PredictCurrentPriceRequest,
    PredictCurrentPriceResponse,
)


class CurrentPricePredictionService:
    def __init__(self, *, model_dir: Path, bundle: CurrentPriceArtifactBundle) -> None:
        self.model_dir = model_dir
        self.bundle = bundle

    @classmethod
    def from_app(cls, app: Flask) -> CurrentPricePredictionService:
        model_dir = Path(app.config["CURRENT_PRICE_MODEL_DIR"])
        existing = app.extensions.get("current_price_prediction_service")
        if isinstance(existing, CurrentPricePredictionService) and existing.model_dir == model_dir:
            return existing

        try:
            bundle = load_current_price_artifacts(model_dir)
        except FileNotFoundError as exc:
            raise ServiceUnavailableError(str(exc)) from exc

        service = cls(model_dir=model_dir, bundle=bundle)
        app.extensions["current_price_prediction_service"] = service
        return service

    def predict(self, payload: PredictCurrentPriceRequest) -> PredictCurrentPriceResponse:
        source_frame = build_inference_source_frame(payload.model_dump(mode="python"))
        title_components = transform_title_text(
            source_frame["title_text"],
            self.bundle.vectorizer,
            self.bundle.svd,
            self.bundle.metadata.title_component_names,
        )
        feature_frame = pd.concat([source_frame.reset_index(drop=True), title_components], axis=1)
        prediction_pool = Pool(
            feature_frame[self.bundle.metadata.feature_names],
            cat_features=self.bundle.metadata.categorical_feature_names,
        )
        predicted_log_price = float(self.bundle.model.predict(prediction_pool)[0])
        predicted_price = max(0.0, float(np.expm1(predicted_log_price)))
        return PredictCurrentPriceResponse(
            predicted_current_price=round(predicted_price, 2),
            model_name=self.bundle.metadata.model_name,
            model_version=self.bundle.metadata.model_version,
            features_version=self.bundle.metadata.features_version,
            warnings=self._warnings_for_payload(payload),
        )

    def _warnings_for_payload(self, payload: PredictCurrentPriceRequest) -> list[str]:
        warnings: list[str] = []
        if payload.brand is None:
            warnings.append("brand missing; using fallback value 'unknown'")
        if payload.seller is None:
            warnings.append("seller missing; using fallback value 'unknown'")
        if payload.gsc_category_id is None:
            warnings.append("gsc_category_id missing; category signal is weaker")
        if not payload.image_urls:
            warnings.append("image_urls missing; image metadata features fall back to empty")
        return warnings
