from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urljoin, urlparse

PRICE_SUFFIX_RE = re.compile(r"\s+")


@dataclass(slots=True)
class NormalizedProductRecord:
    product_id: str
    sku_id: str
    source_domain: str
    source_url: str
    product_url: str
    page_number: int
    position: int
    brand: str | None
    title: str
    seller: str | None
    current_price: Decimal | None
    current_price_text: str | None
    original_price: Decimal | None
    original_price_text: str | None
    discount_text: str | None
    rating: Decimal | None
    review_count: int | None
    sponsored: bool
    raw_text: str
    raw_prices: list[dict[str, Any]]
    raw_payload: dict[str, Any]
    image_urls: list[str]
    scraped_at: datetime


def normalize_search_results(
    *,
    results: list[dict[str, Any]],
    page_number: int,
    source_url: str,
) -> list[NormalizedProductRecord]:
    normalized: list[NormalizedProductRecord] = []
    for position, item in enumerate(results, start=1):
        product_id = _normalize_text(item.get("productId")) or ""
        sku_id = _normalize_text(item.get("skuId")) or product_id
        product_url = _build_product_url(item=item, source_url=source_url)
        source_domain = urlparse(product_url or source_url).netloc
        brand = _normalize_text(item.get("brand"))
        title = _normalize_text(item.get("displayName")) or product_id or sku_id
        seller = _normalize_text(item.get("sellerName"))
        prices = _normalize_prices(item.get("prices"))
        current_entry, original_entry = _split_prices(prices)
        discount_text = _extract_discount(item)
        rating = _parse_decimal(_normalize_text(item.get("rating")))
        review_count = _parse_int(item.get("totalReviews"))
        image_urls = _extract_image_urls(item)
        raw_text = _build_raw_text(
            brand=brand,
            title=title,
            seller=seller,
            current_price_text=current_entry[1],
            original_price_text=original_entry[1],
            discount_text=discount_text,
        )

        normalized.append(
            NormalizedProductRecord(
                product_id=product_id,
                sku_id=sku_id,
                source_domain=source_domain,
                source_url=source_url,
                product_url=product_url,
                page_number=page_number,
                position=position,
                brand=brand,
                title=title,
                seller=seller,
                current_price=current_entry[0],
                current_price_text=current_entry[1],
                original_price=original_entry[0],
                original_price_text=original_entry[1],
                discount_text=discount_text,
                rating=rating,
                review_count=review_count,
                sponsored=bool(item.get("isSponsored")),
                raw_text=raw_text,
                raw_prices=prices,
                raw_payload=item,
                image_urls=image_urls,
                scraped_at=datetime.now(UTC),
            )
        )

    return normalized


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = PRICE_SUFFIX_RE.sub(" ", str(value)).strip()
    return normalized or None


def _normalize_prices(raw_prices: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_prices, list):
        return []
    prices: list[dict[str, Any]] = []
    for raw_price in raw_prices:
        if not isinstance(raw_price, dict):
            continue
        values = raw_price.get("price")
        if not isinstance(values, list):
            values = []
        normalized_values = [_normalize_text(value) for value in values]
        normalized_values = [value for value in normalized_values if value]
        prices.append(
            {
                "symbol": _normalize_symbol(raw_price.get("symbol")),
                "type": _normalize_text(raw_price.get("type")) or "",
                "crossed": bool(raw_price.get("crossed")),
                "values": normalized_values,
            }
        )
    return prices


def _split_prices(
    raw_prices: list[dict[str, Any]],
) -> tuple[tuple[Decimal | None, str | None], tuple[Decimal | None, str | None]]:
    current_entry: dict[str, Any] | None = None
    original_entry: dict[str, Any] | None = None
    for price in raw_prices:
        if price["crossed"] and original_entry is None:
            original_entry = price
        elif not price["crossed"] and current_entry is None:
            current_entry = price

    if current_entry is None and raw_prices:
        current_entry = raw_prices[0]
    if original_entry is None and len(raw_prices) > 1:
        original_entry = raw_prices[1]

    return _serialize_price_entry(current_entry), _serialize_price_entry(original_entry)


def _serialize_price_entry(price: dict[str, Any] | None) -> tuple[Decimal | None, str | None]:
    if price is None:
        return None, None
    values = price.get("values") or []
    if not values:
        return None, None
    symbol = price.get("symbol") or ""
    formatted = " - ".join(f"{symbol}{value}" for value in values)
    numeric_value = _parse_decimal(values[0])
    return numeric_value, formatted


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_symbol(value: Any) -> str:
    if value is None:
        return ""
    symbol = str(value)
    if symbol and not symbol.endswith(" "):
        symbol = f"{symbol} "
    return symbol


def _build_product_url(*, item: dict[str, Any], source_url: str) -> str:
    raw_url = _normalize_text(item.get("url")) or ""
    if not raw_url:
        return source_url
    return urljoin(source_url, raw_url)


def _extract_discount(item: dict[str, Any]) -> str | None:
    badge = item.get("discountBadge")
    if not isinstance(badge, dict):
        return None
    return _normalize_text(badge.get("label"))


def _extract_image_urls(item: dict[str, Any]) -> list[str]:
    image_urls: list[str] = []
    media_urls = item.get("mediaUrls")
    if isinstance(media_urls, list):
        for media_url in media_urls:
            normalized = _normalize_text(media_url)
            if normalized and normalized not in image_urls:
                image_urls.append(normalized)

    media = item.get("media")
    if isinstance(media, dict):
        for value in media.values():
            normalized = _normalize_text(value)
            if normalized and _is_absolute_url(normalized) and normalized not in image_urls:
                image_urls.append(normalized)

    return image_urls


def _build_raw_text(
    *,
    brand: str | None,
    title: str,
    seller: str | None,
    current_price_text: str | None,
    original_price_text: str | None,
    discount_text: str | None,
) -> str:
    tokens = [brand, title, seller, current_price_text, original_price_text, discount_text]
    return " | ".join(token for token in tokens if token)


def _is_absolute_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
