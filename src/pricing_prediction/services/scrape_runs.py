from __future__ import annotations

import time
from typing import Any

from flask import Flask

from pricing_prediction.clients.falabella_client import FalabellaClient
from pricing_prediction.db.models import ScrapeRun, utcnow
from pricing_prediction.db.repositories import ScrapeRunRepository
from pricing_prediction.errors import DomainValidationError
from pricing_prediction.scraper.falabella.next_data import parse_search_page
from pricing_prediction.scraper.falabella.normalize import normalize_search_results


class ScrapeRunService:
    def __init__(
        self,
        *,
        repository: ScrapeRunRepository,
        client: FalabellaClient,
        default_max_pages: int,
        max_allowed_pages: int,
        request_delay_ms: int,
        source: str,
    ) -> None:
        self.repository = repository
        self.client = client
        self.default_max_pages = default_max_pages
        self.max_allowed_pages = max_allowed_pages
        self.request_delay_ms = request_delay_ms
        self.source = source

    @classmethod
    def from_app(cls, app: Flask) -> ScrapeRunService:
        client = FalabellaClient(
            timeout=app.config["SCRAPER_REQUEST_TIMEOUT"],
            retry_attempts=app.config["SCRAPER_RETRY_ATTEMPTS"],
            user_agent=app.config["SCRAPER_USER_AGENT"],
            enable_browser_fallback=app.config["SCRAPER_ENABLE_BROWSER_FALLBACK"],
        )
        return cls(
            repository=ScrapeRunRepository(),
            client=client,
            default_max_pages=app.config["SCRAPER_DEFAULT_MAX_PAGES"],
            max_allowed_pages=app.config["SCRAPER_MAX_ALLOWED_PAGES"],
            request_delay_ms=app.config["SCRAPER_REQUEST_DELAY_MS"],
            source=app.config["SCRAPER_SOURCE"],
        )

    def create_run(self, query: str, max_pages: int | None, source: str) -> ScrapeRun:
        if source != self.source:
            raise DomainValidationError(f"Unsupported scraper source '{source}'.")

        requested_pages = max_pages or self.default_max_pages
        if requested_pages < 1:
            raise DomainValidationError("max_pages must be greater than zero.")
        if requested_pages > self.max_allowed_pages:
            raise DomainValidationError(
                f"max_pages cannot exceed {self.max_allowed_pages} for this environment."
            )

        return self.repository.create_run(
            source=source,
            query=query,
            requested_pages=requested_pages,
        )

    def execute_run(self, run_id: str) -> ScrapeRun:
        page_errors: list[str] = []
        try:
            run = self.repository.get_run(run_id)
            if run.status == "running":
                return run

            run.status = "running"
            run.started_at = run.started_at or utcnow()
            run.error_message = None
            self.repository.commit()

            scraped_pages = run.scraped_pages
            scraped_items = run.scraped_items

            for page_number in range(1, run.requested_pages + 1):
                try:
                    fetched_page = self.client.fetch_search_page(run.query, page_number)
                    parsed_page = parse_search_page(fetched_page.html)
                    items = normalize_search_results(
                        results=parsed_page.results,
                        page_number=page_number,
                        source_url=fetched_page.source_url,
                    )
                    persisted_items = self.repository.persist_page(
                        run_id=run.id,
                        query=run.query,
                        items=items,
                    )
                    scraped_pages += 1
                    scraped_items += persisted_items
                    run = self.repository.get_run(run_id)
                    run.scraped_pages = scraped_pages
                    run.scraped_items = scraped_items
                    self.repository.commit()
                except Exception as exc:
                    page_errors.append(f"page {page_number}: {exc}")
                    self.repository.rollback()
                    run = self.repository.get_run(run_id)
                    run.scraped_pages = scraped_pages
                    run.scraped_items = scraped_items
                    run.error_message = "\n".join(page_errors)
                    self.repository.commit()

                if page_number < run.requested_pages and self.request_delay_ms > 0:
                    time.sleep(self.request_delay_ms / 1000)

            run = self.repository.get_run(run_id)
            run.scraped_pages = scraped_pages
            run.scraped_items = scraped_items
            run.finished_at = utcnow()
            run.error_message = "\n".join(page_errors) if page_errors else None
            run.status = "completed_with_errors" if page_errors else "completed"
            self.repository.commit()
            return run
        finally:
            self.client.close()

    def get_run(self, run_id: str) -> ScrapeRun:
        return self.repository.get_run(run_id)

    def list_run_items(self, run_id: str, limit: int, offset: int) -> dict[str, Any]:
        total, snapshots = self.repository.list_snapshots(run_id, limit, offset)
        return {
            "items": [snapshot.to_dict() for snapshot in snapshots],
            "limit": limit,
            "offset": offset,
            "total": total,
        }
