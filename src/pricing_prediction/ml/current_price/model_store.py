from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import Flask

from pricing_prediction.ml.current_price.artifacts import (
    REQUIRED_CURRENT_PRICE_ARTIFACT_FILENAMES,
    validate_current_price_artifact_dir,
)


def create_s3_client() -> Any:
    import boto3  # type: ignore[import-untyped]

    return boto3.client("s3")


class CurrentPriceModelStore:
    def __init__(
        self,
        *,
        source: str,
        local_model_dir: Path,
        cache_dir: Path,
        s3_bucket: str | None,
        s3_prefix: str | None,
        s3_version: str | None,
        s3_manifest_key: str | None,
        s3_client: Any | None = None,
    ) -> None:
        self.source = source
        self.local_model_dir = local_model_dir
        self.cache_dir = cache_dir
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.s3_version = s3_version
        self.s3_manifest_key = s3_manifest_key
        self.s3_client = s3_client

    @classmethod
    def from_app(cls, app: Flask) -> CurrentPriceModelStore:
        return cls(
            source=str(app.config["MODEL_SOURCE"]),
            local_model_dir=Path(app.config["CURRENT_PRICE_MODEL_DIR"]),
            cache_dir=Path(app.config["CURRENT_PRICE_MODEL_CACHE_DIR"]),
            s3_bucket=app.config["CURRENT_PRICE_MODEL_S3_BUCKET"],
            s3_prefix=app.config["CURRENT_PRICE_MODEL_S3_PREFIX"],
            s3_version=app.config["CURRENT_PRICE_MODEL_S3_VERSION"],
            s3_manifest_key=app.config["CURRENT_PRICE_MODEL_S3_MANIFEST_KEY"],
            s3_client=app.extensions.get("current_price_model_store_s3_client"),
        )

    def resolve_model_dir(self) -> Path:
        if self.source == "local":
            validate_current_price_artifact_dir(self.local_model_dir)
            return self.local_model_dir

        if self.source != "s3":
            raise ValueError(f"Unsupported MODEL_SOURCE '{self.source}'.")
        if self.s3_bucket is None:
            raise ValueError("CURRENT_PRICE_MODEL_S3_BUCKET is required when MODEL_SOURCE=s3.")

        version = self._resolve_model_version()
        target_dir = self.cache_dir / version
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if target_dir.exists():
            try:
                validate_current_price_artifact_dir(target_dir)
                return target_dir
            except FileNotFoundError:
                shutil.rmtree(target_dir, ignore_errors=True)

        temp_dir = self.cache_dir / f".{version}.tmp-{uuid4().hex}"
        temp_dir.mkdir(parents=True, exist_ok=False)
        try:
            for filename in REQUIRED_CURRENT_PRICE_ARTIFACT_FILENAMES:
                self._download_artifact(version, filename, temp_dir / filename)
            validate_current_price_artifact_dir(temp_dir)
            temp_dir.rename(target_dir)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        return target_dir

    def _resolve_model_version(self) -> str:
        if self.s3_version is not None:
            return self.s3_version
        if self.s3_manifest_key is None:
            raise ValueError(
                "CURRENT_PRICE_MODEL_S3_VERSION or CURRENT_PRICE_MODEL_S3_MANIFEST_KEY is required "
                "when MODEL_SOURCE=s3."
            )

        response = self._s3_client().get_object(Bucket=self.s3_bucket, Key=self.s3_manifest_key)
        payload = json.loads(response["Body"].read().decode("utf-8"))
        version = payload.get("model_version") or payload.get("version")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("Model manifest must contain a non-empty 'model_version'.")
        return version.strip()

    def _download_artifact(self, version: str, filename: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        artifact_key = self._artifact_key(version, filename)
        try:
            self._s3_client().download_file(
                self.s3_bucket,
                artifact_key,
                str(destination),
            )
        except Exception as exc:
            raise FileNotFoundError(
                f"Current price model artifact bundle is incomplete in "
                f"'s3://{self.s3_bucket}/{self.s3_prefix}/{version}': missing '{filename}'"
            ) from exc

    def _artifact_key(self, version: str, filename: str) -> str:
        if self.s3_prefix is None:
            raise ValueError("CURRENT_PRICE_MODEL_S3_PREFIX is required when MODEL_SOURCE=s3.")
        prefix = self.s3_prefix.strip("/")
        return f"{prefix}/{version}/{filename}" if prefix else f"{version}/{filename}"

    def _s3_client(self) -> Any:
        if self.s3_client is None:
            self.s3_client = create_s3_client()
        return self.s3_client
