from __future__ import annotations

from collections.abc import Mapping

import pytest

from pricing_prediction.clients.falabella_client import FetchedSearchPage
from pricing_prediction.db.repositories import ScrapeRunRepository
from pricing_prediction.services.scrape_runs import ScrapeRunService


class FakeFalabellaClient:
    def __init__(self, pages: Mapping[int, str]) -> None:
        self.pages = dict(pages)

    def fetch_search_page(self, query: str, page: int) -> FetchedSearchPage:
        return FetchedSearchPage(
            source_url=f"https://www.falabella.com.pe/falabella-pe/search?Ntt={query}&page={page}",
            html=self.pages[page],
        )

    def close(self) -> None:
        return None


@pytest.fixture()
def stub_service_factory(monkeypatch, search_page_1_html: str, search_page_30_html: str):
    def factory(app):
        pages = {page: search_page_1_html for page in range(1, 30)}
        pages[30] = search_page_30_html
        return ScrapeRunService(
            repository=ScrapeRunRepository(),
            client=FakeFalabellaClient(pages),
            default_max_pages=30,
            max_allowed_pages=30,
            request_delay_ms=0,
            source="falabella_pe",
        )

    monkeypatch.setattr(ScrapeRunService, "from_app", classmethod(lambda cls, app: factory(app)))


def test_create_scrape_run_endpoint_executes_inline(client, stub_service_factory) -> None:
    response = client.post(
        "/api/v1/scrape-runs",
        json={"query": "ropa mujer", "max_pages": 2, "source": "falabella_pe"},
    )

    assert response.status_code == 202
    payload = response.get_json()["data"]
    assert payload["status"] == "completed"
    assert payload["requested_pages"] == 2
    assert payload["scraped_pages"] == 2
    assert payload["scraped_items"] == 98


def test_create_scrape_run_endpoint_validates_query(client, stub_service_factory) -> None:
    response = client.post(
        "/api/v1/scrape-runs",
        json={"query": "   ", "max_pages": 2, "source": "falabella_pe"},
    )

    assert response.status_code == 422
    assert response.get_json()["error"]["message"] == "Validation failed"


def test_create_scrape_run_endpoint_enforces_page_limit(client, stub_service_factory) -> None:
    response = client.post(
        "/api/v1/scrape-runs",
        json={"query": "ropa mujer", "max_pages": 31, "source": "falabella_pe"},
    )

    assert response.status_code == 422
    assert "cannot exceed 30" in response.get_json()["error"]["message"]


def test_list_scrape_run_items_endpoint_returns_snapshots(client, stub_service_factory) -> None:
    create_response = client.post(
        "/api/v1/scrape-runs",
        json={"query": "ropa mujer", "max_pages": 1, "source": "falabella_pe"},
    )
    run_id = create_response.get_json()["data"]["id"]

    items_response = client.get(f"/api/v1/scrape-runs/{run_id}/items?limit=5&offset=0")

    assert items_response.status_code == 200
    payload = items_response.get_json()["data"]
    assert payload["total"] == 49
    assert payload["items"][0]["brand"] == "EL TWIST HOME"
    assert payload["items"][0]["image_urls"]
