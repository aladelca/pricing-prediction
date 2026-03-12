from __future__ import annotations

import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from catboost import CatBoostRegressor
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass(frozen=True)
class CurrentPriceArtifactMetadata:
    model_name: str
    model_version: str
    trained_at: str
    target: str
    features_version: str
    feature_names: list[str]
    categorical_feature_names: list[str]
    title_component_names: list[str]
    metrics: dict[str, float]
    fold_metrics: list[dict[str, float]]
    training_row_count: int
    distinct_sku_count: int
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CurrentPriceArtifactMetadata:
        return cls(
            model_name=str(payload["model_name"]),
            model_version=str(payload["model_version"]),
            trained_at=str(payload["trained_at"]),
            target=str(payload["target"]),
            features_version=str(payload["features_version"]),
            feature_names=[str(item) for item in payload["feature_names"]],
            categorical_feature_names=[str(item) for item in payload["categorical_feature_names"]],
            title_component_names=[str(item) for item in payload["title_component_names"]],
            metrics={str(key): float(value) for key, value in payload["metrics"].items()},
            fold_metrics=[
                {str(key): float(value) for key, value in fold.items()}
                for fold in payload["fold_metrics"]
            ],
            training_row_count=int(payload["training_row_count"]),
            distinct_sku_count=int(payload["distinct_sku_count"]),
            params=dict(payload["params"]),
        )


@dataclass(frozen=True)
class CurrentPriceArtifactBundle:
    model: CatBoostRegressor
    vectorizer: TfidfVectorizer
    svd: TruncatedSVD | None
    metadata: CurrentPriceArtifactMetadata
    feature_contract: dict[str, Any]


def save_current_price_artifacts(
    output_dir: Path,
    *,
    model: CatBoostRegressor,
    vectorizer: TfidfVectorizer,
    svd: TruncatedSVD | None,
    metadata: CurrentPriceArtifactMetadata,
    feature_contract: dict[str, Any],
) -> CurrentPriceArtifactBundle:
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_model(str(output_dir / "model.cbm"))
    with (output_dir / "title_vectorizer.pkl").open("wb") as handle:
        pickle.dump(vectorizer, handle)
    with (output_dir / "title_svd.pkl").open("wb") as handle:
        pickle.dump(svd, handle)
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "feature_contract.json").write_text(
        json.dumps(feature_contract, indent=2) + "\n",
        encoding="utf-8",
    )
    return CurrentPriceArtifactBundle(
        model=model,
        vectorizer=vectorizer,
        svd=svd,
        metadata=metadata,
        feature_contract=feature_contract,
    )


def load_current_price_artifacts(model_dir: Path) -> CurrentPriceArtifactBundle:
    required_paths = [
        model_dir / "model.cbm",
        model_dir / "title_vectorizer.pkl",
        model_dir / "title_svd.pkl",
        model_dir / "metadata.json",
        model_dir / "feature_contract.json",
    ]
    missing = [path.name for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Current price model artifact bundle is incomplete in "
            f"'{model_dir}': {', '.join(missing)}"
        )

    model = CatBoostRegressor()
    model.load_model(str(model_dir / "model.cbm"))

    with (model_dir / "title_vectorizer.pkl").open("rb") as handle:
        vectorizer = pickle.load(handle)
    with (model_dir / "title_svd.pkl").open("rb") as handle:
        svd = pickle.load(handle)
    metadata = CurrentPriceArtifactMetadata.from_dict(
        json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    )
    feature_contract = json.loads((model_dir / "feature_contract.json").read_text(encoding="utf-8"))
    return CurrentPriceArtifactBundle(
        model=model,
        vectorizer=vectorizer,
        svd=svd,
        metadata=metadata,
        feature_contract=feature_contract,
    )
