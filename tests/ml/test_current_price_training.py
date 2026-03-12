from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pricing_prediction.db.models import Product, ProductImage, ProductSnapshot, ScrapeRun
from pricing_prediction.extensions import db
from pricing_prediction.ml.current_price.artifacts import load_current_price_artifacts
from pricing_prediction.ml.current_price.data import load_current_price_training_source_frame
from pricing_prediction.ml.current_price.features import (
    TARGET_COLUMN,
    build_feature_frame,
    ensure_no_forbidden_columns,
)
from pricing_prediction.ml.current_price.training import (
    CurrentPriceTrainingConfig,
    train_current_price_model,
)


def _seed_training_rows() -> None:
    run = ScrapeRun(source="falabella_pe", query="zapatillas", requested_pages=2)
    db.session.add(run)
    db.session.flush()

    for sku_index in range(1, 7):
        sku_id = f"sku-{sku_index}"
        brand = "Adidas" if sku_index % 2 == 0 else "Nike"
        query = "zapatillas mujer" if sku_index % 2 == 0 else "ropa hombre"
        title = f"{brand} modelo {sku_index} running essentials"
        product = Product(
            sku_id=sku_id,
            product_id=f"product-{sku_index}",
            canonical_url=f"https://www.falabella.com.pe/{sku_id}",
            source_domain="www.falabella.com.pe",
            brand=brand,
            title=title,
            seller="Falabella",
            raw_payload={},
        )
        db.session.add(product)
        db.session.add(
            ProductImage(
                sku_id=sku_id,
                position=1,
                image_url=f"https://media.falabella.com.pe/falabellaPE/{sku_id}/public",
            )
        )

        base_price = 80 + (sku_index * 15)
        for page_number, position in ((1, sku_index), (2, sku_index + 2)):
            db.session.add(
                ProductSnapshot(
                    run_id=run.id,
                    sku_id=sku_id,
                    query=query,
                    page_number=page_number,
                    position=position,
                    source_url="https://www.falabella.com.pe/falabella-pe/search",
                    product_url=f"https://www.falabella.com.pe/{sku_id}",
                    current_price=Decimal(str(base_price + (page_number * 3))),
                    current_price_text=f"S/ {base_price}",
                    original_price=Decimal(str(base_price + 40)),
                    original_price_text=f"S/ {base_price + 40}",
                    discount_text="20%",
                    rating=Decimal("4.50"),
                    review_count=10 * sku_index,
                    seller="Falabella",
                    sponsored=position % 2 == 0,
                    raw_text="price text should not leak",
                    raw_prices={"current": base_price},
                    raw_payload={
                        "GSCCategoryId": f"G0{sku_index % 3}",
                        "providerName": "falabella" if sku_index % 2 == 0 else "marketplace",
                        "sellerId": f"seller-{sku_index % 2}",
                        "availability": {
                            "internationalShipping": "" if sku_index % 2 == 0 else "yes"
                        },
                        "isBestSeller": sku_index % 2 == 0,
                        "isFrequentProduct": sku_index % 3 == 0,
                        "multipurposeBadges": [{}] * (sku_index % 3),
                        "mediaUrls": [
                            f"https://media.falabella.com.pe/falabellaPE/{sku_id}/public",
                            f"https://media.falabella.com.pe/falabellaPE/{sku_id}/public/2",
                        ],
                    },
                )
            )
    db.session.commit()


def test_load_current_price_training_source_frame_excludes_leaking_columns(app) -> None:
    with app.app_context():
        _seed_training_rows()

        frame = load_current_price_training_source_frame(db.engine)

        assert TARGET_COLUMN in frame.columns
        assert "current_price_text" not in frame.columns
        assert "discount_text" not in frame.columns
        assert "original_price" not in frame.columns
        assert "original_price_text" not in frame.columns
        assert "raw_text" not in frame.columns
        assert "raw_prices" not in frame.columns


def test_build_feature_frame_derives_expected_features(app) -> None:
    with app.app_context():
        _seed_training_rows()
        source_frame = load_current_price_training_source_frame(db.engine)

        feature_frame = build_feature_frame(source_frame)

        first_row = feature_frame.iloc[0]
        assert first_row["query_root"] in {"ropa", "zapatos", "other"}
        assert first_row["query_audience"] in {"women", "men", "other"}
        assert first_row["availability_bucket"] in {"domestic", "international"}
        assert int(first_row["image_count"]) >= 1
        assert float(first_row["review_count_log1p"]) > 0
        assert "title_text" in feature_frame.columns
        ensure_no_forbidden_columns(feature_frame.columns, allowed=[TARGET_COLUMN])


def test_train_current_price_model_persists_artifacts_and_metrics(app, tmp_path: Path) -> None:
    with app.app_context():
        _seed_training_rows()
        output_dir = tmp_path / "trained-current-price-model"

        summary = train_current_price_model(
            db.engine,
            CurrentPriceTrainingConfig(
                output_dir=output_dir,
                model_version="test-training-v1",
                iterations=25,
                depth=4,
                learning_rate=0.2,
                title_max_features=128,
                title_min_df=1,
                title_n_components=6,
            ),
        )

        bundle = load_current_price_artifacts(output_dir)

        assert summary.model_dir == output_dir
        assert summary.model_version == "test-training-v1"
        assert summary.training_row_count == 12
        assert len(summary.fold_metrics) == 5
        assert bundle.metadata.model_name == "cb_leakfree_title_tfidf_deeper"
        assert bundle.metadata.model_version == "test-training-v1"
        assert "rmse" in bundle.metadata.metrics


def test_ensure_no_forbidden_columns_rejects_price_leakage() -> None:
    try:
        ensure_no_forbidden_columns(["query", "current_price_text"])
    except ValueError as exc:
        assert "current_price_text" in str(exc)
    else:
        raise AssertionError("Leakage guard accepted a forbidden price column.")
