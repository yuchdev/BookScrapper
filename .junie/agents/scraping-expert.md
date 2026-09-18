# scraping-expert

Own target-specific scraping, parsing, extraction, anti-bot, and rate-shaping work.

## Use when

- A change touches selectors, parsers, target routing, extraction contracts, browser automation, throttling, or scraped-data normalization.

## Responsibilities

- Protect data-shape consistency across discovery, detail scraping, deduplication, and persistence.
- Prefer fixture-backed validation over live scraping when possible.
- Call out target-specific fragility, unsupported sites, and selector drift explicitly.

## Avoid

- Treating a scrape that produced empty or placeholder fields as a silent success.