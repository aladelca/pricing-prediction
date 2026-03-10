---
name: dev-webscrapper
description: Build and debug browser-based web scrapers with a Selenium-first workflow and agent-browser-assisted site discovery. Use when Codex needs to inspect dynamic websites, dismiss cookie banners, identify stable selectors, paginate listing pages, extract product cards or PDP fields, save JSON or CSV outputs, or prototype repeatable scrapers for marketplaces such as falabella.com.pe.
---

# Dev Web Scrapper

Build scraping work in two passes:

1. Inspect the target with `agent-browser`.
2. Promote the findings into a repeatable Selenium scraper.

Use `agent-browser` for discovery, selector validation, quick screenshots, and
one-off extraction. Use Selenium for repeatable collection, pagination, retries,
and exports.

## Start with reconnaissance

- Open the exact target URL with `agent-browser`.
- Snapshot interactive elements with `agent-browser snapshot -i -C`.
- Dismiss cookie or location banners before collecting selectors.
- Prefer category, search, or seller listing pages over the home page when the
  goal is product extraction.
- Re-snapshot after every navigation or DOM-changing interaction.
- If the rendered DOM is noisy, inspect network traffic before overfitting DOM
  selectors.

Use this quick loop:

```bash
agent-browser open https://www.falabella.com.pe/falabella-pe
agent-browser wait --load networkidle
agent-browser snapshot -i -C
```

## Translate findings into Selenium

- Start from `scripts/falabella_selenium_scaffold.py` when the target is
  Falabella Peru or another Falabella ecosystem storefront.
- Use explicit waits for hydrated content. Avoid fixed sleeps except for short,
  bounded settle windows after navigation or scroll.
- Scroll until product count or page height stabilizes when cards load lazily.
- Save HTML and screenshots when selectors fail so the scraper can be corrected
  from evidence.
- Keep navigation, extraction, parsing, and persistence separate. Do not hide
  all logic in one large script.
- Record both raw and normalized values for prices, ratings, discounts, and
  seller text.

## Normalize the output contract

Always keep these fields, even if some are null:

- `source_url`
- `source_domain`
- `product_url`
- `product_id`
- `page_type`
- `position`
- `brand`
- `title`
- `current_price`
- `current_price_text`
- `original_price`
- `original_price_text`
- `discount_text`
- `rating`
- `seller`
- `sponsored`
- `raw_text`
- `scraped_at`

Keep raw strings alongside parsed numeric fields so later cleanup does not
require another crawl.

## Choose the extraction path intentionally

- Use DOM extraction when the page exposes the product text reliably after
  hydration.
- Use API extraction when network responses already contain structured catalog
  data.
- Use PDP scraping only for fields that do not exist in listing pages, such as
  SKU, seller metadata, variant attributes, or long descriptions.
- Use the home page only for prototyping selectors, never as the main
  production surface.

## References

- Read `references/falabella-pe.md` for site-specific notes captured from
  Falabella Peru on March 10, 2026.
- Read `references/project-shape.md` when scaffolding a maintainable scraper
  project or deciding what should live in the skill versus the project.

## Deliverables for a scraping task

Produce all of these before considering the task complete:

1. A stable target URL choice.
2. A documented selector or extraction strategy.
3. A runnable scraper entry point.
4. A sample output file.
5. A note about fragility points, such as banners, lazy loading, or redirecting
   product domains.
