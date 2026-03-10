from __future__ import annotations

from collections.abc import Mapping

from pricing_prediction.clients.falabella_client import FetchedSearchPage
from pricing_prediction.db.repositories import ScrapeRunRepository
from pricing_prediction.services.scrape_runs import ScrapeRunService


class FakeFalabellaClient:
    def __init__(self, pages: Mapping[int, str], failures: set[int] | None = None) -> None:
        self.pages = dict(pages)
        self.failures = failures or set()
        self.closed = False

    def fetch_search_page(self, query: str, page: int) -> FetchedSearchPage:
        if page in self.failures:
            raise RuntimeError(f"synthetic failure for page {page}")
        html = self.pages[page]
        return FetchedSearchPage(
            source_url=f"https://www.falabella.com.pe/falabella-pe/search?Ntt={query}&page={page}",
            html=html,
        )

    def close(self) -> None:
        self.closed = True


def test_execute_run_scrapes_thirty_pages(
    app, search_page_1_html: str, search_page_30_html: str
) -> None:
    with app.app_context():
        pages = {page: search_page_1_html for page in range(1, 30)}
        pages[30] = search_page_30_html
        client = FakeFalabellaClient(pages)
        service = ScrapeRunService(
            repository=ScrapeRunRepository(),
            client=client,
            default_max_pages=30,
            max_allowed_pages=30,
            request_delay_ms=0,
            source="falabella_pe",
        )
        run = service.create_run(query="ropa mujer", max_pages=30, source="falabella_pe")

        completed_run = service.execute_run(run.id)

        assert completed_run.status == "completed"
        assert completed_run.scraped_pages == 30
        assert completed_run.scraped_items == (29 * 49) + 48
        assert client.closed is True

        payload = service.list_run_items(run.id, limit=10, offset=0)
        assert payload["total"] == (29 * 49) + 48
        assert (
            payload["items"][0]["title"]
            == "Vestido camisero cabosol negro y prints neutros con lazo cintura removible"
        )


def test_execute_run_marks_partial_failures(app, search_page_1_html: str) -> None:
    with app.app_context():
        pages = {
            1: search_page_1_html,
            2: search_page_1_html,
            3: search_page_1_html,
        }
        client = FakeFalabellaClient(pages, failures={2})
        service = ScrapeRunService(
            repository=ScrapeRunRepository(),
            client=client,
            default_max_pages=3,
            max_allowed_pages=30,
            request_delay_ms=0,
            source="falabella_pe",
        )
        run = service.create_run(query="ropa mujer", max_pages=3, source="falabella_pe")

        completed_run = service.execute_run(run.id)

        assert completed_run.status == "completed_with_errors"
        assert completed_run.scraped_pages == 2
        assert completed_run.scraped_items == 98
        assert "page 2" in (completed_run.error_message or "")
