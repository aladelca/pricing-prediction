from __future__ import annotations

from pricing_prediction.web.field_glossary import PREDICTION_FIELD_GLOSSARY


def test_prediction_field_glossary_covers_prediction_form_fields() -> None:
    glossary_fields = {entry.form_name for entry in PREDICTION_FIELD_GLOSSARY}

    assert {
        "query",
        "page_number",
        "position",
        "title",
        "brand",
        "seller",
        "seller_id",
        "source_domain",
        "rating",
        "review_count",
        "gsc_category_id",
        "provider_name",
        "multipurpose_badges_count",
        "sponsored",
        "is_best_seller",
        "is_frequent_product",
        "international_shipping",
        "image_urls_text",
        "image_files",
    } <= glossary_fields
