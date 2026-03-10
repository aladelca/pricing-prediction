from flask import Blueprint

from pricing_prediction.api.scrape_runs import scrape_runs_bp

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")
api_v1.register_blueprint(scrape_runs_bp)

__all__ = ["api_v1"]
