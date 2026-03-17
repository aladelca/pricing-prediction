from flask import Blueprint

from pricing_prediction.api.predictions import predictions_bp
from pricing_prediction.api.scrape_runs import scrape_runs_bp


def create_api_v1(*, include_scrape_routes: bool) -> Blueprint:
    api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")
    api_v1.register_blueprint(predictions_bp)
    if include_scrape_routes:
        api_v1.register_blueprint(scrape_runs_bp)
    return api_v1


__all__ = ["create_api_v1"]
