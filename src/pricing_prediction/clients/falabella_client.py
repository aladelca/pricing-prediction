from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from pricing_prediction.scraper.falabella.browser_fallback import fetch_search_page_html

FALABELLA_SEARCH_URL = "https://www.falabella.com.pe/falabella-pe/search"


@dataclass(slots=True)
class FetchedSearchPage:
    source_url: str
    html: str
    used_browser_fallback: bool = False


class FalabellaClient:
    def __init__(
        self,
        *,
        timeout: float,
        retry_attempts: int,
        user_agent: str,
        enable_browser_fallback: bool,
    ) -> None:
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.enable_browser_fallback = enable_browser_fallback
        self._client = httpx.Client(
            follow_redirects=True,
            headers={
                "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
                "User-Agent": user_agent,
            },
            timeout=timeout,
        )

    @staticmethod
    def build_search_url(query: str, page: int) -> str:
        params = urlencode({"Ntt": query, "page": page})
        return f"{FALABELLA_SEARCH_URL}?{params}"

    def fetch_search_page(self, query: str, page: int) -> FetchedSearchPage:
        url = self.build_search_url(query, page)
        html = self._fetch_html(url)
        if "__NEXT_DATA__" in html:
            return FetchedSearchPage(source_url=url, html=html)

        if not self.enable_browser_fallback:
            return FetchedSearchPage(source_url=url, html=html)

        fallback_html = fetch_search_page_html(url=url, timeout=self.timeout)
        return FetchedSearchPage(
            source_url=url,
            html=fallback_html,
            used_browser_fallback=True,
        )

    def close(self) -> None:
        self._client.close()

    def _fetch_html(self, url: str) -> str:
        retryer = Retrying(
            stop=stop_after_attempt(self.retry_attempts),
            wait=wait_random_exponential(multiplier=1, max=4),
            retry=retry_if_exception_type(httpx.HTTPError),
            reraise=True,
        )
        response: httpx.Response | None = None
        for attempt in retryer:
            with attempt:
                response = self._client.get(url)
                response.raise_for_status()

        if response is None:
            raise httpx.HTTPError(f"Failed to fetch search page: {url}")

        return response.text
