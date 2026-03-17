from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from pricing_prediction.cli import main
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


def test_sync_current_price_model_command_downloads_bundle_from_s3(
    current_price_model_dir: Path,
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from pricing_prediction.ml.current_price import model_store

    prefix = "model"
    version = "test-fixture-v1"
    monkeypatch.setattr(
        model_store,
        "create_s3_client",
        lambda: FakeS3Client(
            _build_s3_objects(current_price_model_dir, prefix=prefix, version=version)
        ),
    )
    monkeypatch.setenv("APP_RUNTIME_MODE", "inference")
    monkeypatch.setenv("MODEL_SOURCE", "s3")
    monkeypatch.setenv("CURRENT_PRICE_MODEL_S3_BUCKET", "pricing-prediction-cibertec")
    monkeypatch.setenv("CURRENT_PRICE_MODEL_S3_PREFIX", prefix)
    monkeypatch.setenv("CURRENT_PRICE_MODEL_S3_MANIFEST_KEY", f"{prefix}/production.json")
    monkeypatch.setenv("CURRENT_PRICE_MODEL_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(sys, "argv", ["pricing-prediction", "sync-current-price-model"])

    exit_code = main()

    assert exit_code == 0
    assert str(tmp_path / "cache" / version) in capsys.readouterr().out
