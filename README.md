# Strategy credit comparison: five preferreds and six convertible-note scenarios

[![Offline verification](https://github.com/RahilBhavan/strategy-credit-curve/actions/workflows/ci.yml/badge.svg)](https://github.com/RahilBhavan/strategy-credit-curve/actions/workflows/ci.yml)

![Six notes priced under nine assumed volatility/spread combinations each, using synthetic stock prices; results are USD per $1,000 face, not market quotes.](figures/scenarios.svg)

An offline Python research tool compares Strategy's five preferred securities and prices six convertible schedules with a Tsiveriotis–Fernandes (TF) tree. Contract terms and government-rate inputs use a frozen October 21, 2026 research snapshot. The public demo uses **independently authored synthetic stock prices and volatility proxies**, with no claim that they were observed in the market. Supply your own dated inputs through a validated JSON file.

## Results

- Five preferred rows in seniority order: STRF, STRC, STRE, STRK and STRD, retaining currency, accumulation, call/put and conversion rights (`results/preferred.json`). These are scenario comparisons, not live rankings or a fitted credit term structure.
- Six notes × nine volatility/spread combinations = **54 model scenarios** (`results/convertibles.json`). Under the central 60% volatility / 5% spread assumptions, public-demo values range from **$884.47 to $1,713.85 per $1,000 face**. Synthetic MSTR spot is $250; these are not observed note prices.
- **39 tests pass**, covering source hashes and quotations, split-adjusted terms, independent analytic TF limits, convergence, coupon-date puts, offline CLI behavior, portable inputs and fetch retries.

## How it works

`inputs.py` validates the market-input file. `market.py` parses attributed government rates and retains optional local market parsers. `curve.py` compares preferreds, `notes.py` builds dated schedules, and `convertible.py` separates TF cash and equity discounting on a CRR tree. `run.py` writes both JSON outputs without network calls. Each output records input kind and file hash; dates for valuation, observation and retrieval remain separate.

## Run it

Tested with Python 3.13.15 and NumPy 2.5.4; Python 3.14.7 also passes locally. No API keys or paid services are needed for the public demo.

```bash
git clone https://github.com/RahilBhavan/strategy-credit-curve.git
cd strategy-credit-curve
python3 -m venv "$HOME/scratch/strategy-credit-curve/venv"
"$HOME/scratch/strategy-credit-curve/venv/bin/python" -m pip install -r requirements.txt
"$HOME/scratch/strategy-credit-curve/venv/bin/python" scripts/restore_data.py
"$HOME/scratch/strategy-credit-curve/venv/bin/python" -m unittest discover -s tests -v
"$HOME/scratch/strategy-credit-curve/venv/bin/python" -m credit_curve.run
"$HOME/scratch/strategy-credit-curve/venv/bin/python" scripts/render_results.py
```

Restoration reconstructs 34 public SEC source files and checks their hashes. The demo writes five preferred comparisons and six nine-scenario note grids to `results/`; the figure is regenerated from the note results. `--out <directory>` changes output destination, and `--steps 1200` changes the default 600-step tree.

For user-supplied prices and volatility proxies, copy the [input example](data/scenarios/market-inputs.json), follow the [input contract](docs/market-inputs.md), and run:

```bash
python -m credit_curve.run --market-input /path/to/your-inputs.json --out results/local
```

Use the installed virtual environment's Python. This frozen tool supports the October 21, 2026 valuation date; changing a file's date does not reconstruct historical data. Obtain any local provider data under its terms. Full Nasdaq, Cboe and Yahoo responses and the original private Git history are **absent from every public commit**.

## Repository layout

- `credit_curve/` — source parsers, input validation, arithmetic and CLI.
- `data/` — public-source ledger, compressed SEC files and instrument terms; synthetic inputs are separate.
- `results/` — generated public-demo scenarios.
- `figures/` — generated result table and review brief.
- `tests/` — numerical, source, input and workflow checks.
- `scripts/` — public-source packing/restoration and figure generation.
- `docs/` — scope, methodology, source coverage, input contract and verification.

## Documentation

- [Public design system](DESIGN.md): Rahil Design 3.3.0, shared tokens and visual review rules.

- [Scope](docs/spec.md) — accepted functionality and sanitized publication.
- [Methodology](docs/methodology.md) — equations, assumptions and omitted features.
- [Sources](docs/sources.md) — public provenance and data-rights boundary.
- [Market inputs](docs/market-inputs.md) — schema and local-input workflow.
- [Verification](docs/verification.md) — checks and their limits.
- [Review](docs/review.md) — demonstrated problems and repairs.
- [Publication receipt](docs/publication.md) — remote and clean-clone evidence.

## Sources

[SEC filings](docs/sources.md) supply terms, split reconciliation and dated fair values. The public ledger contains 67 attributed SEC, Treasury, NY Fed and ECB responses with original retrieval timestamps and SHA-256 hashes. Source: ECB statistics; rates/FX calculations are this project's transformations. [ECB reuse policy](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html) applies to its public statistics. See [sources](docs/sources.md) for ownership and provider exclusions.

## Scope and limits

- Independent research; no affiliation with Strategy or trading recommendation.
- Public market inputs are synthetic. STRE has no verified current quote here and is excluded from live rankings. The original private analysis used its November 6, 2025 €80 offering price; that is not substituted for a current quote. EUR/USD scenarios hold EUR price fixed and omit dividends/costs.
- STRK's perpetual conversion right is approximated by finite European calls. Yield gaps do not isolate a noncumulative-dividend discount.
- Treasury par rates are proxies, not bootstrapped discount curves. Volatility and spread grids are assumptions, not fitted credit spreads.
- Note triggers use nodes rather than 20-of-30-day path tests. Make-whole tables, settlement elections, exact calendars/30-360 accrual, record-date ownership and TF default recovery are omitted. June 30 fair values are stale context.
- Analytic tests validate restricted limits, not full real-contract accuracy or external production/PDE equivalence.
- The October 28, 2026 daily-dividend vote remains **pending at the October 21 cutoff**; no enactment is assumed.

## License

No license file yet. Third-party filings and statistics retain their own rights; no provider-data redistribution permission is claimed.

Part of [Rahil Bhavan's projects](https://github.com/RahilBhavan).
