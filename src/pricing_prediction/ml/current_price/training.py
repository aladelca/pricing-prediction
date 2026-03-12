from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sqlalchemy.engine import Engine

from pricing_prediction.ml.current_price.artifacts import (
    CurrentPriceArtifactMetadata,
    save_current_price_artifacts,
)
from pricing_prediction.ml.current_price.data import load_current_price_training_source_frame
from pricing_prediction.ml.current_price.features import (
    BASE_FEATURE_COLUMNS,
    CAT_FEATURE_COLUMNS,
    FEATURES_VERSION,
    FORBIDDEN_COLUMNS,
    TitleTextTransformConfig,
    build_feature_frame,
    ensure_no_forbidden_columns,
    fit_title_text_transform,
    transform_title_text,
)


@dataclass(frozen=True)
class CurrentPriceTrainingConfig:
    output_dir: Path
    model_name: str = "cb_leakfree_title_tfidf_deeper"
    model_version: str | None = None
    random_state: int = 42
    n_splits: int = 5
    depth: int = 8
    learning_rate: float = 0.05
    iterations: int = 380
    od_wait: int = 40
    sample_limit: int | None = None
    title_max_features: int = 4000
    title_min_df: int = 3
    title_n_components: int = 48

    def text_transform_config(self) -> TitleTextTransformConfig:
        return TitleTextTransformConfig(
            max_features=self.title_max_features,
            min_df=self.title_min_df,
            n_components=self.title_n_components,
        )


@dataclass(frozen=True)
class TrainingSummary:
    model_dir: Path
    model_name: str
    model_version: str
    metrics: dict[str, float]
    fold_metrics: list[dict[str, float]]
    training_row_count: int
    distinct_sku_count: int
    feature_count: int


def _build_model(config: CurrentPriceTrainingConfig) -> CatBoostRegressor:
    return CatBoostRegressor(
        loss_function="RMSE",
        eval_metric="RMSE",
        random_seed=config.random_state,
        depth=config.depth,
        learning_rate=config.learning_rate,
        iterations=config.iterations,
        od_type="Iter",
        od_wait=config.od_wait,
        verbose=False,
        allow_writing_files=False,
    )


def train_current_price_model(
    engine: Engine,
    config: CurrentPriceTrainingConfig,
) -> TrainingSummary:
    source_frame = load_current_price_training_source_frame(engine, limit=config.sample_limit)
    if source_frame.empty:
        raise ValueError("No training rows were loaded for current_price.")

    feature_frame = build_feature_frame(source_frame)
    ensure_no_forbidden_columns(BASE_FEATURE_COLUMNS)
    distinct_sku_count = int(feature_frame["sku_id"].nunique())
    if distinct_sku_count < config.n_splits:
        raise ValueError(
            "Current price training requires at least "
            f"{config.n_splits} distinct sku_id groups; found {distinct_sku_count}."
        )

    splitter = GroupKFold(n_splits=config.n_splits)
    text_config = config.text_transform_config()
    fold_metrics: list[dict[str, float]] = []

    for train_idx, valid_idx in splitter.split(feature_frame, groups=feature_frame["sku_id"]):
        train_df = feature_frame.iloc[train_idx].reset_index(drop=True)
        valid_df = feature_frame.iloc[valid_idx].reset_index(drop=True)

        vectorizer, svd, title_component_names, train_title_components = fit_title_text_transform(
            train_df["title_text"], text_config
        )
        valid_title_components = transform_title_text(
            valid_df["title_text"],
            vectorizer,
            svd,
            title_component_names,
        )
        train_features = pd.concat([train_df, train_title_components], axis=1)
        valid_features = pd.concat([valid_df, valid_title_components], axis=1)
        feature_names = BASE_FEATURE_COLUMNS + title_component_names
        ensure_no_forbidden_columns(feature_names)

        train_pool = Pool(
            train_features[feature_names],
            label=train_features["log_target"],
            cat_features=CAT_FEATURE_COLUMNS,
        )
        valid_pool = Pool(
            valid_features[feature_names],
            label=valid_features["log_target"],
            cat_features=CAT_FEATURE_COLUMNS,
        )
        model = _build_model(config)
        model.fit(train_pool, eval_set=valid_pool, use_best_model=True)

        predictions = np.expm1(model.predict(valid_pool))
        actual = np.expm1(valid_features["log_target"].to_numpy())
        fold_metrics.append(
            {
                "rmse": math.sqrt(mean_squared_error(actual, predictions)),
                "mae": mean_absolute_error(actual, predictions),
                "r2": r2_score(actual, predictions),
            }
        )

    vectorizer, svd, title_component_names, title_components = fit_title_text_transform(
        feature_frame["title_text"], text_config
    )
    final_feature_frame = pd.concat(
        [feature_frame.reset_index(drop=True), title_components], axis=1
    )
    feature_names = BASE_FEATURE_COLUMNS + title_component_names
    ensure_no_forbidden_columns(feature_names)
    final_pool = Pool(
        final_feature_frame[feature_names],
        label=final_feature_frame["log_target"],
        cat_features=CAT_FEATURE_COLUMNS,
    )
    final_model = _build_model(config)
    final_model.fit(final_pool)

    model_version = config.model_version or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    metrics = {
        "rmse": float(np.mean([fold["rmse"] for fold in fold_metrics])),
        "mae": float(np.mean([fold["mae"] for fold in fold_metrics])),
        "r2": float(np.mean([fold["r2"] for fold in fold_metrics])),
    }
    metadata = CurrentPriceArtifactMetadata(
        model_name=config.model_name,
        model_version=model_version,
        trained_at=datetime.now(UTC).isoformat(),
        target="current_price",
        features_version=FEATURES_VERSION,
        feature_names=feature_names,
        categorical_feature_names=list(CAT_FEATURE_COLUMNS),
        title_component_names=title_component_names,
        metrics=metrics,
        fold_metrics=fold_metrics,
        training_row_count=int(len(feature_frame)),
        distinct_sku_count=distinct_sku_count,
        params={
            "depth": config.depth,
            "learning_rate": config.learning_rate,
            "iterations": config.iterations,
            "od_wait": config.od_wait,
            "n_splits": config.n_splits,
            "title_max_features": config.title_max_features,
            "title_min_df": config.title_min_df,
            "title_n_components": len(title_component_names),
        },
    )
    feature_contract = {
        "version": FEATURES_VERSION,
        "base_feature_names": list(BASE_FEATURE_COLUMNS),
        "categorical_feature_names": list(CAT_FEATURE_COLUMNS),
        "title_component_names": title_component_names,
        "forbidden_columns": sorted(FORBIDDEN_COLUMNS),
    }
    save_current_price_artifacts(
        config.output_dir,
        model=final_model,
        vectorizer=vectorizer,
        svd=svd,
        metadata=metadata,
        feature_contract=feature_contract,
    )
    return TrainingSummary(
        model_dir=config.output_dir,
        model_name=config.model_name,
        model_version=model_version,
        metrics=metrics,
        fold_metrics=fold_metrics,
        training_row_count=int(len(feature_frame)),
        distinct_sku_count=distinct_sku_count,
        feature_count=len(feature_names),
    )
