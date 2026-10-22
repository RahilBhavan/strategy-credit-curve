# Portable market inputs

Purpose: supply prices and STRK option-volatility proxies without bundling vendor responses or requiring a live feed.

The public example `data/scenarios/market-inputs.json` is independently authored. Prices (MSTR 250 USD, STRF/STRC 100 USD, STRE 100 EUR, STRK 90 USD, STRD 85 USD) and 60%/80% STRK option volatility are **synthetic assumptions**. They are not observed quotes, calibrated inputs or replacements for the original private cache. Contract terms and government-rate observations remain separately sourced.

## Schema version 1

- `schema_version`: integer 1.
- `kind`: `synthetic_scenario` or `user_supplied`. A user-supplied file is never independently certified as observed or live by the tool.
- `valuation_date`: `2026-10-21`. The frozen term/rate comparison rejects other dates.
- `quotes`: exactly MSTR, STRF, STRC, STRE, STRK and STRD. Each has a positive finite `price`, correct `currency` (STRE EUR, others USD) and `source`.
- `strk_option_volatility`: positive finite `base` and `sensitivity` values, plus `source`. These feed finite 5/10/20-year call scenarios; they are not a fitted perpetual-option model.
- Each `source` requires a nonempty `description`, `as_of` (ISO observation date or null), `fetched_utc` (UTC timestamp or null), and an optional HTTPS `url` or null. Synthetic values require null observation dates. Observation dates after valuation are rejected; retrieval may occur later. Include accurate rights/source context in descriptions, never secrets or credential-bearing URLs.

An input file's byte SHA-256 is recorded in each output. Quotes retain their own source descriptions and dates; note outputs include MSTR spot provenance. Synthetic inputs are labeled, and no row is eligible for a verified live ranking. User observations older than valuation are explicitly stale; missing observation dates produce null staleness rather than an invented date. Invalid data exits 2 before output writes. Inputs that make STRK's assumed option adjustment leave a nonpositive straight-price proxy are rejected explicitly.

## Use locally

Install dependencies and restore the public SEC snapshot as in the README. Copy the example outside the repository (or into ignored `data/local/`), set `kind` to `user_supplied`, and replace values/descriptions/dates with your own authorized data. Then:

```bash
python -m credit_curve.run --market-input /path/to/your-inputs.json --out /path/to/local-results
```

All five preferreds, six note schedules, nine note scenarios each, FX arithmetic, option scenarios, numerical benchmarks and evaluation functions remain available. The default demo never fetches market data.

`market.py` retains Nasdaq/Yahoo/Cboe parsers, and `market_fetch.py` retains optional local acquisition helpers for users with a suitable provider basis. `SEC_USER_AGENT` may be required for new SEC requests. These helpers are not invoked by the public demo or CI. Provider endpoints may change, and a latest quote stored in a date-named directory is not historical reconstruction. Review provider terms yourself; this project grants no access or redistribution rights. Provider response patterns and `data/local/` are ignored by Git. Do not commit your local responses, observations or credentials.
