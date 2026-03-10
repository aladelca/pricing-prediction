from __future__ import annotations

from pricing_prediction.scraper.falabella.next_data import ParsedSearchPage, parse_search_page


def test_parse_search_page_extracts_page_one_results(search_page_1_html: str) -> None:
    parsed = parse_search_page(search_page_1_html)

    assert isinstance(parsed, ParsedSearchPage)
    assert len(parsed.results) == 49
    assert parsed.pagination["currentPage"] == 1
    assert parsed.results[0]["productId"] == "151863579"
    assert parsed.results[0]["skuId"] == "151863580"
    assert parsed.results[0]["brand"] == "EL TWIST HOME"


def test_parse_search_page_extracts_page_thirty_results(search_page_30_html: str) -> None:
    parsed = parse_search_page(search_page_30_html)

    assert len(parsed.results) == 48
    assert parsed.pagination["currentPage"] == 30
    assert parsed.results[0]["productId"] == "883674929"
    assert parsed.results[0]["skuId"] == "883674934"
    assert parsed.results[0]["brand"] == "AMERICAN ABBEY"
