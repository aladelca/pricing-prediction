from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from pricing_prediction.app import create_app
from pricing_prediction.extensions import db
from pricing_prediction.ml.current_price.training import (
    CurrentPriceTrainingConfig,
    train_current_price_model,
)
from pricing_prediction.services.scrape_runs import ScrapeRunService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="pricing-prediction CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape = subparsers.add_parser("scrape-falabella", help="Run a Falabella scrape job.")
    scrape.add_argument("--query", required=True, help="Search term to scrape.")
    scrape.add_argument("--max-pages", type=int, default=30, help="Number of pages to scrape.")

    train_model = subparsers.add_parser(
        "train-current-price-model",
        help="Train the current_price model and persist its artifacts.",
    )
    train_model.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where the model artifact bundle will be written.",
    )
    train_model.add_argument(
        "--model-version",
        default=None,
        help="Optional explicit model version label for the artifact bundle.",
    )
    train_model.add_argument(
        "--sample-limit",
        type=int,
        default=None,
        help="Optional row cap for training smoke tests.",
    )
    train_model.add_argument("--iterations", type=int, default=380)
    train_model.add_argument("--depth", type=int, default=8)
    train_model.add_argument("--learning-rate", type=float, default=0.05)
    train_model.add_argument("--title-max-features", type=int, default=4000)
    train_model.add_argument("--title-min-df", type=int, default=3)
    train_model.add_argument("--title-n-components", type=int, default=48)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    app = create_app({"SCRAPER_INLINE_EXECUTION": True})

    if args.command == "scrape-falabella":
        with app.app_context():
            service = ScrapeRunService.from_app(app)
            run = service.create_run(
                query=args.query,
                max_pages=args.max_pages,
                source=app.config["SCRAPER_SOURCE"],
            )
            completed_run = service.execute_run(run.id)
            print(json.dumps({"run": completed_run.to_dict()}, indent=2))
            return 0

    if args.command == "train-current-price-model":
        with app.app_context():
            summary = train_current_price_model(
                db.engine,
                CurrentPriceTrainingConfig(
                    output_dir=args.output_dir or Path(app.config["CURRENT_PRICE_MODEL_DIR"]),
                    model_version=args.model_version,
                    sample_limit=args.sample_limit,
                    iterations=args.iterations,
                    depth=args.depth,
                    learning_rate=args.learning_rate,
                    title_max_features=args.title_max_features,
                    title_min_df=args.title_min_df,
                    title_n_components=args.title_n_components,
                ),
            )
            print(json.dumps({"training_summary": asdict(summary)}, indent=2, default=str))
            return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
