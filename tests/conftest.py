from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from catboost import CatBoostRegressor, Pool

from pricing_prediction.app import create_app
from pricing_prediction.extensions import db
from pricing_prediction.ml.current_price.artifacts import (
    CurrentPriceArtifactMetadata,
    save_current_price_artifacts,
)
from pricing_prediction.ml.current_price.features import (
    BASE_FEATURE_COLUMNS,
    CAT_FEATURE_COLUMNS,
    FEATURES_VERSION,
    TitleTextTransformConfig,
    build_feature_frame,
    fit_title_text_transform,
)


@pytest.fixture()
def app(tmp_path: Path):
    import pricing_prediction.db.models  # noqa: F401

    database_path = tmp_path / "test.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "SCRAPER_INLINE_EXECUTION": True,
            "SCRAPER_ENABLE_BROWSER_FALLBACK": False,
            "SCRAPER_DEFAULT_MAX_PAGES": 30,
            "SCRAPER_MAX_ALLOWED_PAGES": 30,
            "SCRAPER_REQUEST_DELAY_MS": 0,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def search_page_1_html() -> str:
    return (Path(__file__).parent / "fixtures" / "falabella" / "search_page_1.html").read_text()


@pytest.fixture()
def search_page_30_html() -> str:
    return (Path(__file__).parent / "fixtures" / "falabella" / "search_page_30.html").read_text()


@pytest.fixture()
def current_price_model_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "current-price-model"
    raw_frame = pd.DataFrame(
        [
            {
                "sku_id": "sku-1",
                "query": "zapatillas mujer",
                "page_number": 1,
                "position": 1,
                "title": "Adidas running zapatillas mujer cloudfoam",
                "brand": "Adidas",
                "seller": "Falabella",
                "source_domain": "www.falabella.com.pe",
                "rating": 4.8,
                "review_count": 120,
                "sponsored": False,
                "raw_payload": {
                    "GSCCategoryId": "G01",
                    "providerName": "falabella",
                    "sellerId": "seller-1",
                    "availability": {"internationalShipping": ""},
                    "isBestSeller": True,
                    "isFrequentProduct": False,
                    "multipurposeBadges": [{}],
                    "mediaUrls": [
                        "https://media.falabella.com.pe/falabellaPE/sku-1/public",
                        "https://media.falabella.com.pe/falabellaPE/sku-1/public/2",
                    ],
                },
                "image_count": 2,
                "first_image_url": "https://media.falabella.com.pe/falabellaPE/sku-1/public",
                "current_price": 229.9,
            },
            {
                "sku_id": "sku-2",
                "query": "zapatillas hombre",
                "page_number": 1,
                "position": 5,
                "title": "Nike running zapatillas hombre revolution",
                "brand": "Nike",
                "seller": "Falabella",
                "source_domain": "www.falabella.com.pe",
                "rating": 4.3,
                "review_count": 55,
                "sponsored": False,
                "raw_payload": {
                    "GSCCategoryId": "G01",
                    "providerName": "falabella",
                    "sellerId": "seller-1",
                    "availability": {"internationalShipping": ""},
                    "isBestSeller": False,
                    "isFrequentProduct": False,
                    "multipurposeBadges": [],
                    "mediaUrls": [
                        "https://media.falabella.com.pe/falabellaPE/sku-2/public",
                    ],
                },
                "image_count": 1,
                "first_image_url": "https://media.falabella.com.pe/falabellaPE/sku-2/public",
                "current_price": 189.9,
            },
            {
                "sku_id": "sku-3",
                "query": "zapatillas mujer",
                "page_number": 2,
                "position": 3,
                "title": "Puma zapatillas mujer urban street",
                "brand": "Puma",
                "seller": "ThirdParty",
                "source_domain": "www.falabella.com.pe",
                "rating": 4.1,
                "review_count": 22,
                "sponsored": True,
                "raw_payload": {
                    "GSCCategoryId": "G02",
                    "providerName": "marketplace",
                    "sellerId": "seller-2",
                    "availability": {"internationalShipping": "yes"},
                    "isBestSeller": False,
                    "isFrequentProduct": True,
                    "multipurposeBadges": [{}, {}],
                    "mediaUrls": [
                        "https://images.falabella.com/sku-3/public",
                    ],
                },
                "image_count": 1,
                "first_image_url": "https://images.falabella.com/sku-3/public",
                "current_price": 149.9,
            },
            {
                "sku_id": "sku-4",
                "query": "ropa mujer",
                "page_number": 1,
                "position": 12,
                "title": "Adidas polera mujer essentials sport",
                "brand": "Adidas",
                "seller": "Falabella",
                "source_domain": "www.falabella.com.pe",
                "rating": 4.9,
                "review_count": 180,
                "sponsored": False,
                "raw_payload": {
                    "GSCCategoryId": "G03",
                    "providerName": "falabella",
                    "sellerId": "seller-1",
                    "availability": {"internationalShipping": ""},
                    "isBestSeller": True,
                    "isFrequentProduct": True,
                    "multipurposeBadges": [{}],
                    "mediaUrls": [
                        "https://media.falabella.com.pe/falabellaPE/sku-4/public",
                    ],
                },
                "image_count": 1,
                "first_image_url": "https://media.falabella.com.pe/falabellaPE/sku-4/public",
                "current_price": 129.9,
            },
        ]
    )
    feature_frame = build_feature_frame(raw_frame)
    vectorizer, svd, title_component_names, title_components = fit_title_text_transform(
        feature_frame["title_text"],
        TitleTextTransformConfig(max_features=64, min_df=1, n_components=4),
    )
    train_frame = pd.concat([feature_frame.reset_index(drop=True), title_components], axis=1)
    feature_names = BASE_FEATURE_COLUMNS + title_component_names
    train_pool = Pool(
        train_frame[feature_names],
        label=train_frame["log_target"],
        cat_features=CAT_FEATURE_COLUMNS,
    )
    model = CatBoostRegressor(
        loss_function="RMSE",
        eval_metric="RMSE",
        random_seed=42,
        depth=4,
        learning_rate=0.2,
        iterations=40,
        verbose=False,
        allow_writing_files=False,
    )
    model.fit(train_pool)

    metadata = CurrentPriceArtifactMetadata(
        model_name="cb_leakfree_title_tfidf_deeper",
        model_version="test-fixture-v1",
        trained_at="2026-03-12T00:00:00+00:00",
        target="current_price",
        features_version=FEATURES_VERSION,
        feature_names=feature_names,
        categorical_feature_names=list(CAT_FEATURE_COLUMNS),
        title_component_names=title_component_names,
        metrics={"rmse": 0.0, "mae": 0.0, "r2": 1.0},
        fold_metrics=[],
        training_row_count=len(train_frame),
        distinct_sku_count=int(train_frame["sku_id"].nunique()),
        params={"fixture": True},
    )
    save_current_price_artifacts(
        output_dir,
        model=model,
        vectorizer=vectorizer,
        svd=svd,
        metadata=metadata,
        feature_contract={
            "version": FEATURES_VERSION,
            "base_feature_names": list(BASE_FEATURE_COLUMNS),
            "categorical_feature_names": list(CAT_FEATURE_COLUMNS),
            "title_component_names": title_component_names,
        },
    )
    return output_dir
