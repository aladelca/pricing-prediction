from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from werkzeug.datastructures import FileStorage, MultiDict
from werkzeug.utils import secure_filename

from pricing_prediction.schemas.prediction import PredictCurrentPriceRequest

DEFAULT_SOURCE_DOMAIN = "www.falabella.com.pe"
UPLOAD_PLACEHOLDER_PREFIX = "upload://images/local-upload"


@dataclass(frozen=True)
class PredictionFormSubmission:
    payload: PredictCurrentPriceRequest
    form_values: dict[str, Any]
    image_urls: list[str]
    upload_filenames: list[str]


class PredictionFormValidationError(Exception):
    def __init__(
        self,
        *,
        field_errors: dict[str, str],
        form_values: dict[str, Any],
        image_urls: list[str],
        upload_filenames: list[str],
    ) -> None:
        super().__init__("Prediction form is invalid.")
        self.field_errors = field_errors
        self.form_values = form_values
        self.image_urls = image_urls
        self.upload_filenames = upload_filenames


def default_prediction_form_values() -> dict[str, Any]:
    return {
        "query": "",
        "page_number": "1",
        "position": "1",
        "title": "",
        "brand": "",
        "seller": "",
        "seller_id": "",
        "source_domain": DEFAULT_SOURCE_DOMAIN,
        "rating": "",
        "review_count": "",
        "gsc_category_id": "",
        "provider_name": "",
        "sponsored": False,
        "is_best_seller": False,
        "is_frequent_product": False,
        "multipurpose_badges_count": "0",
        "international_shipping": False,
        "image_urls_text": "",
    }


def parse_prediction_form(
    form: MultiDict[str, str],
    files: MultiDict[str, FileStorage],
    config: Mapping[str, Any],
) -> PredictionFormSubmission:
    form_values = default_prediction_form_values()
    form_values.update(
        {
            "query": form.get("query", "").strip(),
            "page_number": form.get("page_number", "1").strip(),
            "position": form.get("position", "1").strip(),
            "title": form.get("title", "").strip(),
            "brand": form.get("brand", "").strip(),
            "seller": form.get("seller", "").strip(),
            "seller_id": form.get("seller_id", "").strip(),
            "source_domain": form.get("source_domain", DEFAULT_SOURCE_DOMAIN).strip()
            or DEFAULT_SOURCE_DOMAIN,
            "rating": form.get("rating", "").strip(),
            "review_count": form.get("review_count", "").strip(),
            "gsc_category_id": form.get("gsc_category_id", "").strip(),
            "provider_name": form.get("provider_name", "").strip(),
            "sponsored": _checkbox_is_checked(form, "sponsored"),
            "is_best_seller": _checkbox_is_checked(form, "is_best_seller"),
            "is_frequent_product": _checkbox_is_checked(form, "is_frequent_product"),
            "multipurpose_badges_count": form.get("multipurpose_badges_count", "0").strip(),
            "international_shipping": _checkbox_is_checked(form, "international_shipping"),
            "image_urls_text": form.get("image_urls_text", "").strip(),
        }
    )

    upload_filenames = _collect_upload_filenames(files)
    field_errors = _validate_uploaded_files(upload_filenames, config)
    manual_image_urls = _split_image_urls(str(form_values["image_urls_text"]))
    image_urls = manual_image_urls + [
        _build_upload_placeholder(filename) for filename in upload_filenames
    ]

    if field_errors:
        field_errors.setdefault("form", "Review the highlighted fields and submit again.")
        raise PredictionFormValidationError(
            field_errors=field_errors,
            form_values=form_values,
            image_urls=image_urls,
            upload_filenames=upload_filenames,
        )

    payload = {
        "query": form_values["query"],
        "page_number": form_values["page_number"],
        "position": form_values["position"],
        "title": form_values["title"],
        "brand": _optional_string(form_values["brand"]),
        "seller": _optional_string(form_values["seller"]),
        "seller_id": _optional_string(form_values["seller_id"]),
        "source_domain": form_values["source_domain"],
        "rating": _optional_string(form_values["rating"]),
        "review_count": _optional_string(form_values["review_count"]),
        "sponsored": form_values["sponsored"],
        "gsc_category_id": _optional_string(form_values["gsc_category_id"]),
        "provider_name": _optional_string(form_values["provider_name"]),
        "availability": {
            "internationalShipping": "available" if form_values["international_shipping"] else ""
        },
        "image_urls": image_urls,
        "is_best_seller": form_values["is_best_seller"],
        "is_frequent_product": form_values["is_frequent_product"],
        "multipurpose_badges_count": _optional_string(form_values["multipurpose_badges_count"])
        or "0",
    }

    try:
        parsed_payload = PredictCurrentPriceRequest.model_validate(payload)
    except ValidationError as exc:
        field_errors = _map_validation_errors(exc)
        field_errors.setdefault("form", "Review the highlighted fields and submit again.")
        raise PredictionFormValidationError(
            field_errors=field_errors,
            form_values=form_values,
            image_urls=image_urls,
            upload_filenames=upload_filenames,
        ) from exc

    return PredictionFormSubmission(
        payload=parsed_payload,
        form_values=form_values,
        image_urls=image_urls,
        upload_filenames=upload_filenames,
    )


def _checkbox_is_checked(form: MultiDict[str, str], field_name: str) -> bool:
    return form.get(field_name) == "on"


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    return normalized or None


def _split_image_urls(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _collect_upload_filenames(files: MultiDict[str, FileStorage]) -> list[str]:
    filenames: list[str] = []
    for upload in files.getlist("image_files"):
        if not upload.filename:
            continue
        filename = secure_filename(upload.filename)
        if filename:
            filenames.append(filename)
    return filenames


def _validate_uploaded_files(
    upload_filenames: list[str],
    config: Mapping[str, Any],
) -> dict[str, str]:
    errors: dict[str, str] = {}
    max_files = int(config.get("WEB_PREDICTION_MAX_IMAGE_FILES", 6))
    if len(upload_filenames) > max_files:
        errors["image_files"] = f"You can upload up to {max_files} images per prediction."
        return errors

    allowed_extensions = {
        str(extension).lower()
        for extension in config.get(
            "WEB_PREDICTION_ALLOWED_EXTENSIONS",
            ("jpg", "jpeg", "png", "webp"),
        )
    }
    for filename in upload_filenames:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension not in allowed_extensions:
            allowed = ", ".join(sorted(allowed_extensions))
            errors["image_files"] = f"Unsupported file type. Allowed extensions: {allowed}."
            break
    return errors


def _build_upload_placeholder(filename: str) -> str:
    return f"{UPLOAD_PLACEHOLDER_PREFIX}/{filename}"


def _map_validation_errors(error: ValidationError) -> dict[str, str]:
    field_errors: dict[str, str] = {}
    for item in error.errors():
        location = item.get("loc", ())
        if not location:
            continue
        field_name = str(location[0])
        if field_name == "availability":
            field_name = "international_shipping"
        field_errors.setdefault(field_name, str(item.get("msg", "Invalid value")))
    return field_errors or {"form": "Validation failed."}
