# Project shape

## Skill shape

Keep the skill lean and procedural:

```text
dev-webscrapper/
  SKILL.md
  agents/openai.yaml
  references/falabella-pe.md
  references/project-shape.md
  scripts/falabella_selenium_scaffold.py
```

Put only reusable workflows and reference material in the skill. Put
scraper-specific business logic in the actual project that uses the skill.

## Scraper project layout

Use this shape for a maintainable scraping project:

```text
scraper/
  cli.py
  config.py
  drivers/
    chrome.py
  targets/
    falabella/
      navigation.py
      listing.py
      pdp.py
      parse.py
  pipelines/
    jsonl.py
    csv.py
  schemas/
    product.py
tests/
  fixtures/
  test_parse_falabella.py
snapshots/
  html/
  screenshots/
output/
```

## Responsibilities

- `navigation.py`: open pages, dismiss banners, paginate, scroll, retry
- `listing.py`: collect listing cards and positions
- `pdp.py`: collect detail-only fields
- `parse.py`: normalize prices, ratings, seller strings, and ids
- `pipelines/`: write JSONL, CSV, or database records
- `tests/`: lock parsing behavior against saved HTML fixtures

## Engineering rules

- Keep selectors close to the target module that owns them.
- Keep parsing pure so it can be unit tested without Selenium.
- Save one raw HTML fixture per important page type.
- Add a debug bundle on failure: URL, screenshot, and page source.
- Avoid scraping logic in notebooks first. Build a CLI that can be scheduled.

## When to stop using the home page

Move off the home page as soon as you know:

- which listing URL you want
- which fields you need
- which banner or modal blocks extraction

The home page is good for reconnaissance. It is bad for production
repeatability.
