from __future__ import annotations

import argparse
import json

from pricing_prediction.app import create_app
from pricing_prediction.services.scrape_runs import ScrapeRunService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="pricing-prediction CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape = subparsers.add_parser("scrape-falabella", help="Run a Falabella scrape job.")
    scrape.add_argument("--query", required=True, help="Search term to scrape.")
    scrape.add_argument("--max-pages", type=int, default=30, help="Number of pages to scrape.")
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

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
