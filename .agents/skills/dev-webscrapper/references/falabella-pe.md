# Falabella Peru notes

## Scope

These notes are for `https://www.falabella.com.pe/falabella-pe` and adjacent
Falabella ecosystem domains.

The page was inspected with `agent-browser` on March 10, 2026.

## What the inspection showed

- The home page is heavily promotional and not a stable extraction surface.
- A cookie consent button labeled `Aceptar` is present and should be dismissed
  early.
- Product promos appear as clickable links whose accessible text usually
  concatenates:
  - brand
  - title
  - rating
  - current price
  - discount
  - original price
  - optional `Patrocinado`
- Clicking a product from the Falabella home page can redirect to another
  Falabella ecosystem domain. During inspection, a JVC speaker card redirected
  to:

```text
https://tottus.falabella.com.pe/tottus-pe/product/144798298/parlante-bluetooth-jvc-5w-ipx7-grey/144798300
```

Treat `source_domain` as first-class data. Do not assume every PDP stays on
`www.falabella.com.pe`.

## Practical guidance

- Prefer category, brand, search, or seller result pages over the home page.
- Keep both the listing URL and the PDP URL in the output.
- Expect lazy loading and carousels. Scroll and wait for the page to settle
  before extracting.
- Expect repeated cards and sponsored slots. Deduplicate by resolved product
  URL.
- Keep `raw_text` for each card because the accessible label often contains
  more information than the visible nested nodes expose cleanly.

## Recommended collection order

1. Find a stable listing page.
2. Extract listing cards first.
3. Deduplicate URLs.
4. Visit PDPs only for missing fields.
5. Save a debug HTML snapshot when the expected number of cards drops
   unexpectedly.

## Suggested product schema

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

## Agent-browser reconnaissance recipe

```bash
agent-browser open https://www.falabella.com.pe/falabella-pe
agent-browser wait --load networkidle
agent-browser snapshot -i -C
```

If the cookie banner is present, click the latest ref whose label is
`Aceptar`, then snapshot again before deciding on selectors.

## Selenium hints

- Use explicit waits, not blind sleeps.
- Wait for anchors with price text when starting from a listing-style page.
- Capture screenshots and page source on failure because Falabella surfaces can
  change by campaign.
- Keep URL normalization in one place so cross-domain PDPs are handled
  consistently.
