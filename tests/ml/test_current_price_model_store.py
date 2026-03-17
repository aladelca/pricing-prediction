from __future__ import annotations

import io
import json
from pathlib import Path

from pricing_prediction.ml.current_price.artifacts import REQUIRED_CURRENT_PRICE_ARTIFACT_FILENAMES
from pricing_prediction.ml.current_price.model_store import CurrentPriceModelStore


class FakeS3Client:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = dict(objects)
        self.download_calls: list[tuple[str, str]] = []

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        self.download_calls.append((bucket, key))
        Path(filename).write_bytes(self.objects[key])

    def get_object(self, Bucket: str, Key: str) -> dict[str, io.BytesIO]:
        return {"Body": io.BytesIO(self.objects[Key])}


def _build_s3_objects(model_dir: Path, *, prefix: str, version: str) -> dict[str, bytes]:
    objects: dict[str, bytes] = {}
    for filename in REQUIRED_CURRENT_PRICE_ARTIFACT_FILENAMES:
        objects[f"{prefix}/{version}/{filename}"] = (model_dir / filename).read_bytes()
    objects[f"{prefix}/production.json"] = json.dumps({"model_version": version}).encode("utf-8")
    return objects


def test_model_store_downloads_bundle_and_reuses_cache(
    current_price_model_dir: Path,
    tmp_path: Path,
) -> None:
    version = "test-fixture-v1"
    prefix = "current_price"
    client = FakeS3Client(
        _build_s3_objects(current_price_model_dir, prefix=prefix, version=version)
    )
    store = CurrentPriceModelStore(
        source="s3",
        local_model_dir=tmp_path / "unused-local-dir",
        cache_dir=tmp_path / "cache",
        s3_bucket="pricing-models",
        s3_prefix=prefix,
        s3_version=None,
        s3_manifest_key=f"{prefix}/production.json",
        s3_client=client,
    )

    first_dir = store.resolve_model_dir()
    second_dir = store.resolve_model_dir()

    assert first_dir == tmp_path / "cache" / version
    assert second_dir == first_dir
    assert len(client.download_calls) == len(REQUIRED_CURRENT_PRICE_ARTIFACT_FILENAMES)
    assert all(
        (first_dir / filename).exists() for filename in REQUIRED_CURRENT_PRICE_ARTIFACT_FILENAMES
    )


def test_model_store_raises_when_s3_bundle_is_incomplete(
    current_price_model_dir: Path,
    tmp_path: Path,
) -> None:
    version = "test-fixture-v1"
    prefix = "current_price"
    objects = _build_s3_objects(current_price_model_dir, prefix=prefix, version=version)
    objects.pop(f"{prefix}/{version}/metadata.json")
    client = FakeS3Client(objects)
    store = CurrentPriceModelStore(
        source="s3",
        local_model_dir=tmp_path / "unused-local-dir",
        cache_dir=tmp_path / "cache",
        s3_bucket="pricing-models",
        s3_prefix=prefix,
        s3_version=version,
        s3_manifest_key=None,
        s3_client=client,
    )

    try:
        store.resolve_model_dir()
    except FileNotFoundError as exc:
        assert "metadata.json" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for incomplete S3 bundle.")
