from __future__ import annotations

from decimal import Decimal

from pricing_prediction.scraper.falabella.next_data import parse_search_page
from pricing_prediction.scraper.falabella.normalize import normalize_search_results


def test_normalize_search_results_preserves_listing_fields(search_page_1_html: str) -> None:
    parsed = parse_search_page(search_page_1_html)
    items = normalize_search_results(
        results=parsed.results[:2],
        page_number=1,
        source_url="https://www.falabella.com.pe/falabella-pe/search?Ntt=ropa+mujer&page=1",
    )

    first = items[0]
    second = items[1]

    assert first.product_id == "151863579"
    assert first.sku_id == "151863580"
    assert first.brand == "EL TWIST HOME"
    assert (
        first.title == "Vestido camisero cabosol negro y prints neutros con lazo cintura removible"
    )
    assert first.seller == "ElTwistHome"
    assert first.current_price == Decimal("189")
    assert first.current_price_text == "S/ 189"
    assert first.original_price == Decimal("240")
    assert first.original_price_text == "S/ 240"
    assert first.discount_text == "-21%"
    assert first.image_urls[0].endswith("/151863580_01/public")
    assert first.sponsored is True

    assert second.product_id == "883638477"
    assert second.sku_id == "883638478"
    assert second.current_price == Decimal("99.90")
    assert second.original_price is None
    assert second.rating == Decimal("4.7143")
    assert second.review_count == 7
    assert second.sponsored is False


def test_normalize_search_results_supports_price_ranges() -> None:
    items = normalize_search_results(
        results=[
            {
                "productId": "123",
                "skuId": "456",
                "brand": "GIOIO",
                "displayName": "Vestido Mujer Azul",
                "sellerName": "Good Life23 Pe",
                "url": "/falabella-pe/product/123/demo",
                "prices": [
                    {
                        "symbol": "S/ ",
                        "crossed": False,
                        "type": "internetPrice",
                        "price": ["99", "109"],
                    },
                    {
                        "symbol": "S/ ",
                        "crossed": True,
                        "type": "normalPrice",
                        "price": ["121"],
                    },
                ],
                "mediaUrls": ["https://media.falabella.com.pe/demo/public"],
            }
        ],
        page_number=2,
        source_url="https://www.falabella.com.pe/falabella-pe/search?Ntt=ropa+mujer&page=2",
    )

    item = items[0]

    assert item.current_price == Decimal("99")
    assert item.current_price_text == "S/ 99 - S/ 109"
    assert item.original_price == Decimal("121")
    assert item.original_price_text == "S/ 121"
