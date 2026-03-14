from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, render_template, request

from pricing_prediction.errors import ServiceUnavailableError
from pricing_prediction.services.current_price_predictions import CurrentPricePredictionService
from pricing_prediction.web.forms import (
    PredictionFormSubmission,
    PredictionFormValidationError,
    default_prediction_form_values,
    parse_prediction_form,
)

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def home() -> tuple[str, int]:
    return render_template("home.html", active_page="home"), 200


@web_bp.route("/predict", methods=["GET", "POST"])
def predict() -> tuple[str, int]:
    context = _prediction_page_context()
    if request.method == "GET":
        return render_template("predict.html", **context), 200

    try:
        submission = parse_prediction_form(request.form, request.files, current_app.config)
    except PredictionFormValidationError as exc:
        context.update(
            form_values=exc.form_values,
            field_errors=exc.field_errors,
            image_urls=exc.image_urls,
            upload_filenames=exc.upload_filenames,
        )
        return render_template("predict.html", **context), 422

    context.update(
        form_values=submission.form_values,
        image_urls=submission.image_urls,
        upload_filenames=submission.upload_filenames,
    )
    return _render_prediction_result(submission, context)


def _prediction_page_context() -> dict[str, Any]:
    return {
        "active_page": "predict",
        "form_values": default_prediction_form_values(),
        "field_errors": {},
        "image_urls": [],
        "upload_filenames": [],
        "result": None,
        "service_error": None,
    }


def _render_prediction_result(
    submission: PredictionFormSubmission,
    context: dict[str, Any],
) -> tuple[str, int]:
    try:
        prediction = CurrentPricePredictionService.from_app(current_app).predict(submission.payload)
    except ServiceUnavailableError as exc:
        context["service_error"] = str(exc)
        return render_template("predict.html", **context), 503

    context["result"] = prediction
    return render_template("predict.html", **context), 200
