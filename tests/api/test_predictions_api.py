from __future__ import annotations

from pathlib import Path


def test_predict_current_price_returns_prediction(
    app,
    client,
    current_price_model_dir: Path,
) -> None:
    app.config["CURRENT_PRICE_MODEL_DIR"] = current_price_model_dir
    app.extensions.pop("current_price_prediction_service", None)

    response = client.post(
        "/api/v1/predictions/current-price",
        json={
            "query": "zapatillas mujer",
            "page_number": 1,
            "position": 2,
            "title": "Adidas zapatillas mujer running cloudfoam",
            "brand": "Adidas",
            "seller": "Falabella",
            "source_domain": "www.falabella.com.pe",
            "rating": 4.7,
            "review_count": 88,
            "sponsored": False,
            "gsc_category_id": "G01",
            "provider_name": "falabella",
            "availability": {"internationalShipping": ""},
            "image_urls": [
                "https://media.falabella.com.pe/falabellaPE/sku-10/public",
            ],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["predicted_current_price"] > 0
    assert payload["currency"] == "PEN"
    assert payload["model_name"] == "cb_leakfree_title_tfidf_deeper"
    assert payload["model_version"] == "test-fixture-v1"
    assert payload["target"] == "current_price"


def test_predict_current_price_validates_payload(client) -> None:
    response = client.post(
        "/api/v1/predictions/current-price",
        json={
            "query": "   ",
            "page_number": 1,
            "position": 1,
            "title": "",
        },
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "Validation failed"


def test_predict_current_price_returns_503_when_model_is_missing(
    app, client, tmp_path: Path
) -> None:
    app.config["CURRENT_PRICE_MODEL_DIR"] = tmp_path / "missing-model"
    app.extensions.pop("current_price_prediction_service", None)

    response = client.post(
        "/api/v1/predictions/current-price",
        json={
            "query": "ropa mujer",
            "page_number": 1,
            "position": 1,
            "title": "Polera mujer deportiva",
        },
    )

    assert response.status_code == 503
    assert "artifact bundle is incomplete" in response.get_json()["error"]["message"]
