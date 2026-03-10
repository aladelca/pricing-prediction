from __future__ import annotations

from typing import Any, cast

from flask import Blueprint, current_app, jsonify, request

from pricing_prediction.schemas.scrape import CreateScrapeRunRequest, ListRunItemsQuery
from pricing_prediction.services.scrape_runs import ScrapeRunService

scrape_runs_bp = Blueprint("scrape_runs", __name__)


def _execute_run_with_app(app: Any, run_id: str) -> None:
    with app.app_context():
        service = ScrapeRunService.from_app(app)
        service.execute_run(run_id)


@scrape_runs_bp.post("/scrape-runs")
def create_scrape_run() -> tuple[Any, int]:
    payload = CreateScrapeRunRequest.model_validate(request.get_json(silent=True) or {})
    service = ScrapeRunService.from_app(current_app)
    run = service.create_run(payload.query, payload.max_pages, payload.source)

    if current_app.config["SCRAPER_INLINE_EXECUTION"]:
        run = service.execute_run(run.id)
    else:
        app = cast(Any, current_app)._get_current_object()
        executor = current_app.extensions["scrape_executor"]
        executor.submit(_execute_run_with_app, app, run.id)

    return jsonify({"data": run.to_dict()}), 202


@scrape_runs_bp.get("/scrape-runs/<string:run_id>")
def get_scrape_run(run_id: str) -> tuple[Any, int]:
    service = ScrapeRunService.from_app(current_app)
    run = service.get_run(run_id)
    return jsonify({"data": run.to_dict()}), 200


@scrape_runs_bp.get("/scrape-runs/<string:run_id>/items")
def list_scrape_run_items(run_id: str) -> tuple[Any, int]:
    params = ListRunItemsQuery.model_validate(request.args.to_dict())
    service = ScrapeRunService.from_app(current_app)
    payload = service.list_run_items(run_id, params.limit, params.offset)
    return jsonify({"data": payload}), 200
