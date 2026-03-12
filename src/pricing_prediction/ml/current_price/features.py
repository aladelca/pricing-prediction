from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

FEATURES_VERSION = "v1"
TITLE_COMPONENT_PREFIX = "title_component_"
TARGET_COLUMN = "current_price"
FORBIDDEN_COLUMNS = frozenset(
    {
        "current_price_text",
        "discount_text",
        "original_price",
        "original_price_text",
        "raw_text",
        "raw_prices",
        "price",
        "prices",
    }
)
BASE_FEATURE_COLUMNS = [
    "query",
    "query_root",
    "query_audience",
    "brand",
    "seller",
    "seller_id",
    "source_domain",
    "gsc_category_id",
    "provider_name",
    "availability_bucket",
    "image_namespace",
    "page_number",
    "position",
    "rank_position",
    "rating",
    "rating_missing",
    "review_count_log1p",
    "image_count",
    "media_url_count",
    "title_word_count",
    "title_char_count",
    "title_digit_count",
    "title_has_pack",
    "title_has_kids_token",
    "title_has_sport_token",
    "brand_in_title",
    "sponsored",
    "payload_is_best_seller",
    "payload_is_frequent_product",
    "multi_badge_count",
]
CAT_FEATURE_COLUMNS = [
    "query",
    "query_root",
    "query_audience",
    "brand",
    "seller",
    "seller_id",
    "source_domain",
    "gsc_category_id",
    "provider_name",
    "availability_bucket",
    "image_namespace",
]


@dataclass(frozen=True)
class TitleTextTransformConfig:
    max_features: int = 4000
    min_df: int = 3
    n_components: int = 48
    ngram_min: int = 1
    ngram_max: int = 2


def ensure_no_forbidden_columns(
    columns: Sequence[str],
    *,
    allowed: Sequence[str] = (),
) -> None:
    allowed_set = set(allowed)
    present = sorted((set(columns) - allowed_set).intersection(FORBIDDEN_COLUMNS))
    if present:
        raise ValueError(f"Leaking columns detected: {', '.join(present)}")


def parse_payload(raw_payload: object) -> dict[str, Any]:
    if isinstance(raw_payload, str):
        try:
            loaded = json.loads(raw_payload)
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}
    if isinstance(raw_payload, Mapping):
        return dict(raw_payload)
    return {}


def query_root(value: str) -> str:
    text = value.lower()
    if "zapatos" in text or "zapat" in text or "calzado" in text:
        return "zapatos"
    if "ropa" in text:
        return "ropa"
    return "other"


def query_audience(value: str) -> str:
    text = value.lower()
    if "niñ" in text or "nino" in text or "niño" in text:
        return "kids"
    if "mujer" in text:
        return "women"
    if "hombre" in text:
        return "men"
    return "other"


def image_namespace(image_url: object) -> str:
    if not isinstance(image_url, str):
        return "missing"
    parts = image_url.split("/")
    return parts[3] if len(parts) > 3 else "missing"


def availability_bucket(availability: Mapping[str, Any] | None) -> str:
    if availability is None:
        return "unknown"
    if availability.get("internationalShipping"):
        return "international"
    return "domestic"


def safe_payload_features(raw_payload: object) -> dict[str, object]:
    payload = parse_payload(raw_payload)
    media_urls = payload.get("mediaUrls") or []
    badges = payload.get("multipurposeBadges") or []
    return {
        "gsc_category_id": str(payload.get("GSCCategoryId") or "unknown"),
        "provider_name": str(payload.get("providerName") or "unknown"),
        "seller_id": str(payload.get("sellerId") or "unknown"),
        "availability_bucket": availability_bucket(payload.get("availability")),
        "payload_is_best_seller": int(bool(payload.get("isBestSeller"))),
        "payload_is_frequent_product": int(bool(payload.get("isFrequentProduct"))),
        "multi_badge_count": len(badges),
        "media_url_count": len(media_urls),
    }


def build_feature_frame(raw_frame: pd.DataFrame) -> pd.DataFrame:
    ensure_no_forbidden_columns(raw_frame.columns, allowed=[TARGET_COLUMN])
    frame = raw_frame.copy()
    if "raw_payload" in frame.columns:
        parsed = frame["raw_payload"].map(safe_payload_features).apply(pd.Series)
        frame = pd.concat([frame.drop(columns=["raw_payload"]), parsed], axis=1)

    frame["query"] = frame["query"].fillna("").astype(str)
    frame["query_root"] = frame["query"].map(query_root)
    frame["query_audience"] = frame["query"].map(query_audience)
    frame["brand"] = frame["brand"].fillna("unknown").astype(str)
    frame["seller"] = frame["seller"].fillna("unknown").astype(str)
    frame["seller_id"] = frame["seller_id"].fillna("unknown").astype(str)
    frame["source_domain"] = frame["source_domain"].fillna("www.falabella.com.pe").astype(str)
    frame["gsc_category_id"] = frame["gsc_category_id"].fillna("unknown").astype(str)
    frame["provider_name"] = frame["provider_name"].fillna("unknown").astype(str)
    frame["availability_bucket"] = frame["availability_bucket"].fillna("unknown").astype(str)
    frame["image_namespace"] = frame["first_image_url"].map(image_namespace)
    frame["rating_missing"] = frame["rating"].isna().astype(int)
    frame["rating"] = frame["rating"].fillna(frame["rating"].median() if not frame.empty else 0.0)
    frame["review_count"] = frame["review_count"].fillna(0).astype(int)
    frame["review_count_log1p"] = frame["review_count"].map(lambda value: float(np.log1p(value)))
    frame["image_count"] = (
        frame["image_count"].fillna(frame.get("media_url_count", 0)).fillna(0).astype(int)
    )
    frame["media_url_count"] = (
        frame["media_url_count"].fillna(frame["image_count"]).fillna(0).astype(int)
    )
    frame["title"] = frame["title"].fillna("").astype(str)
    frame["title_word_count"] = frame["title"].str.split().str.len().fillna(0).astype(int)
    frame["title_char_count"] = frame["title"].str.len().fillna(0).astype(int)
    frame["title_digit_count"] = frame["title"].str.count(r"\d").astype(int)
    frame["title_has_pack"] = (
        frame["title"].str.contains(r"pack|set|kit", case=False, regex=True).astype(int)
    )
    frame["title_has_kids_token"] = (
        frame["title"].str.contains(r"niñ|nino|niño|kid|junior", case=False, regex=True).astype(int)
    )
    frame["title_has_sport_token"] = (
        frame["title"]
        .str.contains(r"deportivo|running|trek|outdoor|gym|sport", case=False, regex=True)
        .astype(int)
    )
    frame["brand_in_title"] = (
        (frame["brand"].str.lower() != "unknown")
        & frame.apply(
            lambda row: str(row["brand"]).lower() in str(row["title"]).lower(),
            axis=1,
        )
    ).astype(int)
    frame["sponsored"] = frame["sponsored"].astype(int)
    frame["page_number"] = frame["page_number"].astype(int)
    frame["position"] = frame["position"].astype(int)
    frame["rank_position"] = (frame["page_number"] - 1) * 48 + frame["position"]
    frame["payload_is_best_seller"] = frame["payload_is_best_seller"].fillna(0).astype(int)
    frame["payload_is_frequent_product"] = (
        frame["payload_is_frequent_product"].fillna(0).astype(int)
    )
    frame["multi_badge_count"] = frame["multi_badge_count"].fillna(0).astype(int)
    frame["title_text"] = (
        (
            frame["brand"].fillna("").astype(str)
            + " "
            + frame["query"].fillna("").astype(str)
            + " "
            + frame["title"].fillna("").astype(str)
        )
        .str.lower()
        .str.strip()
    )
    frame.loc[frame["title_text"] == "", "title_text"] = "__missing_title__"
    if TARGET_COLUMN in frame.columns:
        frame[TARGET_COLUMN] = frame[TARGET_COLUMN].astype(float)
        frame["log_target"] = frame[TARGET_COLUMN].map(lambda value: float(np.log1p(value)))
    ensure_no_forbidden_columns(BASE_FEATURE_COLUMNS)
    return frame


def component_feature_names(component_count: int) -> list[str]:
    return [f"{TITLE_COMPONENT_PREFIX}{index + 1}" for index in range(component_count)]


def fit_title_text_transform(
    texts: pd.Series,
    config: TitleTextTransformConfig,
) -> tuple[TfidfVectorizer, TruncatedSVD | None, list[str], pd.DataFrame]:
    vectorizer = TfidfVectorizer(
        max_features=config.max_features,
        min_df=config.min_df,
        ngram_range=(config.ngram_min, config.ngram_max),
    )
    matrix = vectorizer.fit_transform(texts.fillna("__missing_title__"))
    if matrix.shape[1] <= 1:
        dense = matrix.toarray()
        columns = component_feature_names(dense.shape[1])
        return vectorizer, None, columns, pd.DataFrame(dense, columns=columns)

    component_count = min(config.n_components, matrix.shape[1] - 1)
    svd = TruncatedSVD(n_components=component_count, random_state=42)
    transformed = svd.fit_transform(matrix)
    columns = component_feature_names(transformed.shape[1])
    return vectorizer, svd, columns, pd.DataFrame(transformed, columns=columns)


def transform_title_text(
    texts: pd.Series,
    vectorizer: TfidfVectorizer,
    svd: TruncatedSVD | None,
    columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    matrix = vectorizer.transform(texts.fillna("__missing_title__"))
    if svd is None:
        transformed = matrix.toarray()
        resolved_columns = list(columns or component_feature_names(transformed.shape[1]))
        return pd.DataFrame(transformed, columns=resolved_columns)
    transformed = svd.transform(matrix)
    resolved_columns = list(columns or component_feature_names(transformed.shape[1]))
    return pd.DataFrame(transformed, columns=resolved_columns)


def build_inference_source_frame(payload: Mapping[str, Any]) -> pd.DataFrame:
    image_urls = list(payload.get("image_urls", []))
    availability_payload = payload.get("availability")
    availability_mapping = (
        dict(availability_payload) if isinstance(availability_payload, Mapping) else {}
    )
    raw_payload = {
        "GSCCategoryId": payload.get("gsc_category_id"),
        "providerName": payload.get("provider_name"),
        "sellerId": payload.get("seller_id"),
        "availability": availability_mapping,
        "isBestSeller": payload.get("is_best_seller", False),
        "isFrequentProduct": payload.get("is_frequent_product", False),
        "multipurposeBadges": [{}] * int(payload.get("multipurpose_badges_count", 0)),
        "mediaUrls": image_urls,
    }
    frame = pd.DataFrame(
        [
            {
                "sku_id": "inference",
                "query": payload.get("query", ""),
                "page_number": payload.get("page_number", 1),
                "position": payload.get("position", 1),
                "title": payload.get("title", ""),
                "brand": payload.get("brand"),
                "seller": payload.get("seller"),
                "source_domain": payload.get("source_domain", "www.falabella.com.pe"),
                "rating": payload.get("rating"),
                "review_count": payload.get("review_count"),
                "sponsored": payload.get("sponsored", False),
                "raw_payload": raw_payload,
                "image_count": len(image_urls),
                "first_image_url": image_urls[0] if image_urls else None,
            }
        ]
    )
    return build_feature_frame(frame)
