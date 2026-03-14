from __future__ import annotations

from io import BytesIO
from pathlib import Path


def test_home_page_renders_html(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Estimate current marketplace prices" in html
    assert "Start a prediction" in html


def test_predict_page_renders_form(client) -> None:
    response = client.get("/predict")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Generate a current price estimate" in html
    assert 'name="query"' in html
    assert 'name="image_files"' in html
    assert 'href="/predict/help"' in html


def test_field_guide_page_renders_dictionary_entries(client) -> None:
    response = client.get("/predict/help")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Prediction field guide" in html
    assert "Search by field name, API key, definition, or example" in html
    assert "Search query" in html
    assert "availability.internationalShipping" in html
    assert "Image URLs" in html


def test_predict_page_returns_prediction(app, client, current_price_model_dir: Path) -> None:
    app.config["CURRENT_PRICE_MODEL_DIR"] = current_price_model_dir
    app.extensions.pop("current_price_prediction_service", None)

    response = client.post(
        "/predict",
        data={
            "query": "ropa mujer",
            "page_number": "1",
            "position": "4",
            "title": "Polera mujer sport essentials",
            "rating": "4.2",
            "review_count": "12",
            "image_urls_text": "https://images.example/look-1",
        },
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Prediction result" in html
    assert "cb_leakfree_title_tfidf_deeper" in html
    assert "https://images.example/look-1" in html


def test_predict_page_rejects_invalid_form(client) -> None:
    response = client.post(
        "/predict",
        data={
            "query": "   ",
            "page_number": "1",
            "position": "1",
            "title": "",
        },
    )

    assert response.status_code == 422
    html = response.get_data(as_text=True)
    assert "Form validation failed" in html
    assert "Review the highlighted fields and submit again." in html
    assert "field-error" in html


def test_predict_page_accepts_uploaded_files(app, client, current_price_model_dir: Path) -> None:
    app.config["CURRENT_PRICE_MODEL_DIR"] = current_price_model_dir
    app.extensions.pop("current_price_prediction_service", None)

    response = client.post(
        "/predict",
        data={
            "query": "ropa mujer",
            "page_number": "1",
            "position": "4",
            "title": "Polera mujer sport essentials",
            "image_files": [
                (BytesIO(b"fake-image"), "look-1.png"),
            ],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "upload://images/local-upload/look-1.png" in html


def test_predict_page_shows_service_error_when_model_is_missing(
    app,
    client,
    tmp_path: Path,
) -> None:
    app.config["CURRENT_PRICE_MODEL_DIR"] = tmp_path / "missing-model"
    app.extensions.pop("current_price_prediction_service", None)

    response = client.post(
        "/predict",
        data={
            "query": "ropa mujer",
            "page_number": "1",
            "position": "1",
            "title": "Polera mujer deportiva",
        },
    )

    assert response.status_code == 503
    html = response.get_data(as_text=True)
    assert "Prediction service unavailable." in html
    assert "artifact bundle is incomplete" in html
