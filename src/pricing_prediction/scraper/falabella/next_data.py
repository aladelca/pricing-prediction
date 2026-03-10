from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup


class NextDataNotFoundError(ValueError):
    pass


@dataclass(slots=True)
class ParsedSearchPage:
    results: list[dict[str, Any]]
    pagination: dict[str, Any]
    current_url: str | None
    listing_url: str | None


def parse_search_page(html: str) -> ParsedSearchPage:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if script is None or not script.string:
        raise NextDataNotFoundError("Falabella HTML does not contain __NEXT_DATA__.")

    payload = json.loads(script.string)
    page_props = payload.get("props", {}).get("pageProps", {})
    results = page_props.get("results")
    if not isinstance(results, list):
        raise NextDataNotFoundError("Falabella pageProps.results is missing.")

    pagination = page_props.get("pagination", {})
    if not isinstance(pagination, dict):
        pagination = {}

    current_url = page_props.get("currentUrl")
    listing_url = page_props.get("listingUrl")
    return ParsedSearchPage(
        results=results,
        pagination=pagination,
        current_url=current_url if isinstance(current_url, str) else None,
        listing_url=listing_url if isinstance(listing_url, str) else None,
    )
