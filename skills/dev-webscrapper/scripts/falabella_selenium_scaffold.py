#!/usr/bin/env python3
"""
Starter Selenium scraper for Falabella ecosystem listing-style pages.

This script is intentionally conservative. It uses heuristics to collect
product-like anchors whose text contains Sol prices, then writes the results
to JSONL, JSON, or CSV. Tighten the extraction rules once reconnaissance
has identified a more stable listing surface.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

PRICE_RE = re.compile(r"S/\s?[\d.,]+")
DISCOUNT_RE = re.compile(r"-\d+%")
FLOAT_TOKEN_RE = re.compile(r"\b\d(?:\.\d)?\b")
TRAILING_RATING_RE = re.compile(r"\s+\d(?:\.\d)?\s*$")

EXTRACT_SCRIPT = """
const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
const priceRe = /S\\/\\s?[\\d.,]+/g;
const sponsoredRe = /patrocinado/i;
const allowedHostRe = /(falabella\\.com\\.pe|tottus\\.falabella\\.com\\.pe|sodimac\\.falabella\\.com\\.pe|linio\\.falabella\\.com\\.pe)/i;

const seen = new Set();
const results = [];

for (const anchor of document.querySelectorAll("a[href]")) {
  const href = anchor.href || "";
  if (!href || !allowedHostRe.test(href)) {
    continue;
  }

  const text = normalize(
    anchor.innerText ||
    anchor.getAttribute("aria-label") ||
    anchor.textContent
  );

  if (!text || text.length < 12) {
    continue;
  }

  const prices = text.match(priceRe) || [];
  if (prices.length === 0) {
    continue;
  }

  if (seen.has(href)) {
    continue;
  }

  seen.add(href);
  results.push({
    href,
    text,
    prices,
    sponsored: sponsoredRe.test(text),
  });
}

return results;
"""


@dataclass
class ProductRecord:
    source_url: str
    source_domain: str
    product_url: str
    product_id: str | None
    page_type: str
    position: int
    brand: str | None
    title: str
    current_price: float | None
    current_price_text: str | None
    original_price: float | None
    original_price_text: str | None
    discount_text: str | None
    rating: float | None
    seller: str | None
    sponsored: bool
    raw_text: str
    scraped_at: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect product-like links from Falabella ecosystem pages."
    )
    parser.add_argument("url", help="Listing or home URL to inspect.")
    parser.add_argument(
        "-o",
        "--output",
        default="output/falabella-products.jsonl",
        help="Output path. Parent directories will be created.",
    )
    parser.add_argument(
        "--format",
        choices=("jsonl", "json", "csv"),
        default="jsonl",
        help="Output format.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run a visible browser instead of headless Chrome.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Wait timeout in seconds for page hydration.",
    )
    parser.add_argument(
        "--wait-after-open",
        type=float,
        default=2.0,
        help="Small settle delay after opening the page.",
    )
    parser.add_argument(
        "--scroll-steps",
        type=int,
        default=4,
        help="Maximum number of lazy-load scroll passes.",
    )
    parser.add_argument(
        "--scroll-pause",
        type=float,
        default=1.5,
        help="Pause between scroll passes.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=80,
        help="Stop after this many unique candidate records.",
    )
    parser.add_argument(
        "--debug-dir",
        help="Optional directory for failure screenshots and HTML snapshots.",
    )
    return parser.parse_args()


def build_driver(headless: bool):
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError as exc:
        raise SystemExit(
            "selenium is required. Install it with: pip install selenium"
        ) from exc

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,2400")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.page_load_strategy = "eager"

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver


def dismiss_cookie_banner(driver, timeout: float) -> bool:
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait

    locators = (
        (By.XPATH, "//button[normalize-space()='Aceptar']"),
        (By.XPATH, "//button[contains(., 'Aceptar')]"),
    )

    for locator in locators:
        try:
            button = WebDriverWait(driver, timeout).until(
                ec.element_to_be_clickable(locator)
            )
        except TimeoutException:
            continue

        try:
            button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", button)
        time.sleep(0.5)
        return True

    return False


def scroll_until_stable(driver, steps: int, pause: float) -> None:
    last_height = 0
    stable_rounds = 0

    for _ in range(max(0, steps)):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(max(0.0, pause))
        height = int(driver.execute_script("return document.body.scrollHeight") or 0)
        if height == last_height:
            stable_rounds += 1
            if stable_rounds >= 2:
                break
        else:
            stable_rounds = 0
            last_height = height


def wait_for_candidates(driver, timeout: float) -> None:
    from selenium.webdriver.support.ui import WebDriverWait

    WebDriverWait(driver, timeout).until(
        lambda current_driver: len(current_driver.execute_script(EXTRACT_SCRIPT)) > 0
    )


def normalize_price(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = text.replace("S/", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def derive_product_id(url: str) -> str | None:
    matches = re.findall(r"/product/(\\d+)|/(\\d+)(?:\\D*)?$", url)
    if not matches:
        return None
    left, right = matches[-1]
    return left or right or None


def derive_title(raw_text: str) -> str:
    head = PRICE_RE.split(raw_text, maxsplit=1)[0].strip()
    head = TRAILING_RATING_RE.sub("", head).strip()
    return head


def derive_rating(raw_text: str) -> float | None:
    head = PRICE_RE.split(raw_text, maxsplit=1)[0]
    tokens = FLOAT_TOKEN_RE.findall(head)
    for token in reversed(tokens):
        try:
            value = float(token)
        except ValueError:
            continue
        if 0.0 <= value <= 5.0:
            return value
    return None


def derive_brand(title: str) -> str | None:
    if not title:
        return None
    token = title.split(" ", 1)[0].strip(".,:-/")
    if len(token) < 2 or len(token) > 24:
        return None
    if not any(character.isalpha() for character in token):
        return None
    return token


def collect_candidates(driver, source_url: str, max_items: int) -> list[ProductRecord]:
    raw_candidates = driver.execute_script(EXTRACT_SCRIPT)
    source_domain = source_url.split("/")[2]
    now = datetime.now(timezone.utc).isoformat()
    records: list[ProductRecord] = []

    for position, candidate in enumerate(raw_candidates, start=1):
        if len(records) >= max_items:
            break

        raw_text = " ".join(str(candidate["text"]).split())
        title = derive_title(raw_text)
        price_texts = list(dict.fromkeys(candidate.get("prices") or []))
        current_price_text = price_texts[0] if price_texts else None
        original_price_text = price_texts[1] if len(price_texts) > 1 else None
        discount_match = DISCOUNT_RE.search(raw_text)

        records.append(
            ProductRecord(
                source_url=source_url,
                source_domain=source_domain,
                product_url=candidate["href"],
                product_id=derive_product_id(candidate["href"]),
                page_type="listing",
                position=position,
                brand=derive_brand(title),
                title=title,
                current_price=normalize_price(current_price_text),
                current_price_text=current_price_text,
                original_price=normalize_price(original_price_text),
                original_price_text=original_price_text,
                discount_text=discount_match.group(0) if discount_match else None,
                rating=derive_rating(raw_text),
                seller=None,
                sponsored=bool(candidate.get("sponsored")),
                raw_text=raw_text,
                scraped_at=now,
            )
        )

    return records


def write_output(records: list[ProductRecord], output_path: Path, file_format: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(record) for record in records]

    if file_format == "jsonl":
        output_path.write_text(
            "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows)
        )
        return

    if file_format == "json":
        output_path.write_text(json.dumps(rows, ensure_ascii=True, indent=2))
        return

    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_debug_bundle(driver, debug_dir: Path) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    screenshot_path = debug_dir / f"{timestamp}.png"
    html_path = debug_dir / f"{timestamp}.html"
    driver.save_screenshot(str(screenshot_path))
    html_path.write_text(driver.page_source)


def main() -> int:
    args = parse_args()
    driver = build_driver(headless=not args.headed)

    try:
        driver.get(args.url)
        dismiss_cookie_banner(driver, timeout=min(5.0, args.timeout))
        time.sleep(max(0.0, args.wait_after_open))
        scroll_until_stable(driver, steps=args.scroll_steps, pause=args.scroll_pause)
        wait_for_candidates(driver, timeout=args.timeout)
        records = collect_candidates(
            driver,
            source_url=args.url,
            max_items=args.max_items,
        )

        if not records:
            if args.debug_dir:
                save_debug_bundle(driver, Path(args.debug_dir))
            print("No product candidates were found.", file=sys.stderr)
            return 2

        write_output(records, Path(args.output), args.format)
        print(f"Wrote {len(records)} records to {args.output}")
        return 0
    except Exception as exc:
        if args.debug_dir:
            save_debug_bundle(driver, Path(args.debug_dir))
        print(f"Scrape failed: {exc}", file=sys.stderr)
        return 1
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
