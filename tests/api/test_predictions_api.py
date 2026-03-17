from __future__ import annotations

import io
import json
from pathlib import Path

from pricing_prediction.ml.current_price.artifacts import REQUIRED_CURRENT_PRICE_ARTIFACT_FILENAMES


class FakeS3Client:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = dict(objects)

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        _ = bucket
        Path(filename).write_bytes(self.objects[key])

    def get_object(self, Bucket: str, Key: str) -> dict[str, io.BytesIO]:
        _ = Bucket
        return {"Body": io.BytesIO(self.objects[Key])}


def _build_s3_objects(model_dir: Path, *, prefix: str, version: str) -> dict[str, bytes]:
    objects: dict[str, bytes] = {}
    for filename in REQUIRED_CURRENT_PRICE_ARTIFACT_FILENAMES:
        objects[f"{prefix}/{version}/{filename}"] = (model_dir / filename).read_bytes()
    objects[f"{prefix}/production.json"] = json.dumps({"model_version": version}).encode("utf-8")
    return objects


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


def test_predict_current_price_downloads_bundle_from_s3(
    app,
    client,
    current_price_model_dir: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    from pricing_prediction.ml.current_price import model_store

    version = "test-fixture-v1"
    prefix = "current_price"
    monkeypatch.setattr(
        model_store,
        "create_s3_client",
        lambda: FakeS3Client(
            _build_s3_objects(current_price_model_dir, prefix=prefix, version=version)
        ),
    )
    app.config.update(
        {
            "MODEL_SOURCE": "s3",
            "CURRENT_PRICE_MODEL_DIR": tmp_path / "unused-local-dir",
            "CURRENT_PRICE_MODEL_CACHE_DIR": tmp_path / "model-cache",
            "CURRENT_PRICE_MODEL_S3_BUCKET": "pricing-models",
            "CURRENT_PRICE_MODEL_S3_PREFIX": prefix,
            "CURRENT_PRICE_MODEL_S3_MANIFEST_KEY": f"{prefix}/production.json",
            "CURRENT_PRICE_MODEL_S3_VERSION": None,
        }
    )
    app.extensions.pop("current_price_prediction_service", None)

    response = client.post(
        "/api/v1/predictions/current-price",
        json={
            "query": "zapatillas mujer",
            "page_number": 1,
            "position": 2,
            "title": "Adidas zapatillas mujer running cloudfoam",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["model_version"] == "test-fixture-v1"
