from __future__ import annotations

from pathlib import Path


def test_healthcheck_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "pricing-prediction"}


def test_readiness_returns_ok_when_model_is_available(
    app,
    client,
    current_price_model_dir: Path,
) -> None:
    app.config["CURRENT_PRICE_MODEL_DIR"] = current_price_model_dir
    app.extensions.pop("current_price_prediction_service", None)

    response = client.get("/ready")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready"
    assert payload["model_version"] == "test-fixture-v1"


def test_readiness_returns_503_when_model_is_missing(
    app,
    client,
    tmp_path: Path,
) -> None:
    app.config["CURRENT_PRICE_MODEL_DIR"] = tmp_path / "missing-model"
    app.extensions.pop("current_price_prediction_service", None)

    response = client.get("/ready")

    assert response.status_code == 503
    assert "artifact bundle is incomplete" in response.get_json()["error"]["message"]
