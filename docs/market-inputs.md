# Portable market inputs

Purpose: supply prices and STRK option-volatility proxies without bundling vendor responses or requiring a live feed.

The default input `data/market/2026-10-21/closes.json` holds Nasdaq daily closes for MSTR, STRF, STRC, STRK and STRD on October 21, 2026, written by `scripts/fetch_closes.py`. Each close keeps its response URL, retrieval time, byte count and SHA-256, plus a Yahoo Finance cross-check that agrees to the cent. Response bodies stay in ignored `data/local/`. STRE has a null price and an `unavailable` reason: its last Luxembourg Stock Exchange bar with traded volume is January 29, 2026. The STRK option volatilities in that file are authored assumptions.

The example `data/scenarios/market-inputs.json` is independently authored. Prices (MSTR 250 USD, STRF/STRC 100 USD, STRE 100 EUR, STRK 90 USD, STRD 85 USD) and 60%/80% STRK option volatility are **synthetic assumptions**. They are not observed quotes, calibrated inputs or replacements for the original private cache. Contract terms and government-rate observations remain separately sourced.

## Schema version 1

- `schema_version`: integer 1.
- `kind`: `exchange_close`, `synthetic_scenario` or `user_supplied`. An `exchange_close` price must have `as_of` equal to `valuation_date`, an HTTPS `url`, `fetched_utc` and the response `sha256`. A user-supplied file is never independently certified as observed or live by the tool.
- `valuation_date`: ISO date on or after `2026-10-21` (the contract-terms snapshot) and before the earliest note maturity. Any date other than 2026-10-21 requires a rates file (below); contract terms stay at the October 21 snapshot.
- `quotes`: exactly MSTR, STRF, STRC, STRE, STRK and STRD. Each has a positive finite `price`, correct `currency` (STRE EUR, others USD) and `source`. A preferred may instead have `price: null` with a nonempty `unavailable` reason; that row is excluded from yields. MSTR always needs a price.
- `strk_option_volatility`: positive finite `base` and `sensitivity` values, plus `source`. These feed finite 5/10/20-year call scenarios; they are not a fitted perpetual-option model.
- `note_assumptions` (optional): per-note `volatility` (decimal, 0.6 = 60%, range 0.01–5), `credit_spread` (decimal, 0.05 = 500 bp, range 0–0.5) and `source`, for any subset of 2028, 2029, 2030A, 2030B, 2031 and 2032. Each supplied pair is valued in `supplied_assumption` beside the unchanged nine-point grid and appears in the terminal summary.
- Each `source` requires a nonempty `description`, `as_of` (ISO observation date or null), `fetched_utc` (UTC timestamp or null), and an optional HTTPS `url` or null. Synthetic values require null observation dates. Observation dates after valuation are rejected; retrieval may occur later. Include accurate rights/source context in descriptions, never secrets or credential-bearing URLs.

An input file's byte SHA-256 is recorded in each output. Quotes retain their own source descriptions and dates; note outputs include MSTR spot provenance. Synthetic inputs are labeled, and no row is eligible for a verified live ranking. User observations older than valuation are explicitly stale; missing observation dates produce null staleness rather than an invented date. Invalid data exits 2 before output writes. Inputs that make STRK's assumed option adjustment leave a nonpositive straight-price proxy are rejected explicitly.

## Rates file, schema version 1

The bundled rates come from the attributed October 21, 2026 public snapshot. For any other valuation date pass `--rates FILE` (also accepted by `credit_curve.diagnostics`). The example `data/scenarios/later-date/rates.json` is synthetic. Keys must be exactly:

- `schema_version`: integer 1. `kind`: `synthetic_scenario` or `user_supplied`. `valuation_date`: must equal the market file's date.
- `ust_par_yield`: `tenors`, a map from years (`"0.25"`, `"1"`, `"30"`) to Treasury par bond-equivalent yields as decimals, plus `source`. The 30-year tenor and one tenor of 1 year or less are required; other maturities are linearly interpolated.
- `sofr`, `ecb_aaa_spot_30y` (continuously compounded) and `eurusd` (USD per EUR): each `{"rate": number, "source": {...}}`.

Rates must lie in [-0.05, 0.5] and EUR/USD in [0.2, 5]; a value such as `4.5` is rejected with a reminder that 4.5% is `0.045`. Sources follow the same rules as quotes: synthetic files use null observation dates and observations after the valuation date are rejected. The output records the rates kind, date and file SHA-256 under `market_inputs.rates`.

## Use locally

Install dependencies and restore the public SEC snapshot as in the README. Copy the example outside the repository (or into ignored `data/local/`), set `kind` to `user_supplied`, and replace values/descriptions/dates with your own authorized data. Then:

```bash
python -m credit_curve.run --market-input /path/to/your-inputs.json --out /path/to/local-results
```

All five preferred rows, six note schedules, nine note scenarios each, FX arithmetic, option scenarios, numerical benchmarks and evaluation functions remain available. The default demo never fetches market data.

`market.py` retains Nasdaq/Yahoo/Cboe parsers, and `market_fetch.py` retains optional local acquisition helpers for users with a suitable provider basis. `SEC_USER_AGENT` may be required for new SEC requests. These helpers are not invoked by the public demo or CI. Provider endpoints may change, and a latest quote stored in a date-named directory is not historical reconstruction. Review provider terms yourself; this project grants no access or redistribution rights. Provider response patterns and `data/local/` are ignored by Git. Do not commit your local responses, observations or credentials.
