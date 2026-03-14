from __future__ import annotations

from io import BytesIO

from werkzeug.datastructures import FileMultiDict, MultiDict

from pricing_prediction.web.forms import (
    PredictionFormValidationError,
    parse_prediction_form,
)


def test_parse_prediction_form_builds_request_with_urls_and_uploads() -> None:
    form = MultiDict(
        {
            "query": "ropa mujer",
            "page_number": "1",
            "position": "2",
            "title": "Polera mujer sport essentials",
            "brand": "Adidas",
            "image_urls_text": "https://images.example/item-1\nhttps://images.example/item-2",
            "international_shipping": "on",
            "is_best_seller": "on",
        }
    )
    files = FileMultiDict()
    files.add_file("image_files", BytesIO(b"fake-image"), "look-1.png")
    files.add_file("image_files", BytesIO(b"fake-image"), "look-2.webp")

    submission = parse_prediction_form(
        form,
        files,
        {
            "WEB_PREDICTION_MAX_IMAGE_FILES": 4,
            "WEB_PREDICTION_ALLOWED_EXTENSIONS": ("png", "webp"),
        },
    )

    assert submission.payload.query == "ropa mujer"
    assert submission.payload.availability.internationalShipping == "available"
    assert submission.payload.is_best_seller is True
    assert submission.payload.image_urls == [
        "https://images.example/item-1",
        "https://images.example/item-2",
        "upload://images/local-upload/look-1.png",
        "upload://images/local-upload/look-2.webp",
    ]
    assert submission.upload_filenames == ["look-1.png", "look-2.webp"]


def test_parse_prediction_form_rejects_unsupported_file_extension() -> None:
    form = MultiDict(
        {
            "query": "ropa mujer",
            "page_number": "1",
            "position": "2",
            "title": "Polera mujer sport essentials",
        }
    )
    files = FileMultiDict()
    files.add_file("image_files", BytesIO(b"fake-image"), "look-1.gif")

    try:
        parse_prediction_form(
            form,
            files,
            {
                "WEB_PREDICTION_MAX_IMAGE_FILES": 4,
                "WEB_PREDICTION_ALLOWED_EXTENSIONS": ("png", "webp"),
            },
        )
    except PredictionFormValidationError as exc:
        assert exc.field_errors["image_files"].startswith("Unsupported file type")
        assert exc.upload_filenames == ["look-1.gif"]
    else:
        raise AssertionError("Expected an unsupported file type validation error.")


def test_parse_prediction_form_rejects_too_many_files() -> None:
    form = MultiDict(
        {
            "query": "ropa mujer",
            "page_number": "1",
            "position": "2",
            "title": "Polera mujer sport essentials",
        }
    )
    files = FileMultiDict()
    files.add_file("image_files", BytesIO(b"a"), "1.png")
    files.add_file("image_files", BytesIO(b"b"), "2.png")
    files.add_file("image_files", BytesIO(b"c"), "3.png")

    try:
        parse_prediction_form(
            form,
            files,
            {
                "WEB_PREDICTION_MAX_IMAGE_FILES": 2,
                "WEB_PREDICTION_ALLOWED_EXTENSIONS": ("png",),
            },
        )
    except PredictionFormValidationError as exc:
        assert exc.field_errors["image_files"] == "You can upload up to 2 images per prediction."
    else:
        raise AssertionError("Expected a too-many-files validation error.")
