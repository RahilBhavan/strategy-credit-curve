# Verification record

Purpose: record tested public behavior, distinct from source observations and model assumptions.

## Reproduction

Use the README commands: install `numpy==2.5.4`, run `scripts/restore_data.py`, run `python -m unittest discover -s tests -v`, then `python -m credit_curve.run` and `python scripts/render_results.py`. The suite passes **60 tests** with Python 3.13.15 (observed October 22, 2026). No provider credentials are used. Tests/demo use no network after package installation.

The default CLI emits five preferred rows (STRE excluded for lack of a trade) and six nine-scenario grids from the frozen October 21, 2026 Nasdaq closes. It records kind, valuation date, input-file hash and per-input observation/retrieval provenance. Same-environment public outputs and the SVG are byte-repeatable. Across platforms, saved floating references use relative tolerance 1e-12 and absolute tolerance 1e-10, with actual/reference/delta paths printed. JSON types, schema, text, counts and order remain exact. A checker regression rejects meaningful numerical/schema drift; independent analytic invariants remain unchanged. The figure shows grid extrema, not confidence intervals.

## Evidence exercised

- The 22 original numerical/source tests continue, adapted to the public input labels and public-source ledger. They cover split reconciliation, filing quotations, all public-source hashes, independent no-credit and positive-credit European TF limits, bond PV, convergence, calls, puts and invalid pricing inputs.
- A regression for an off-grid coupon-date put failed before the fix ($955.9974818331 against analytic $965.5574566514) and passes after it. Contractual-date cash entitlement now survives grid snapping.
- Mocked 429 retry/success writes one verified response and reuses the cache; exhausted 503 retries leave the previous body/manifest unchanged. Failed source acquisition returns exit status 1.
- The real CLI runs twice with `urlopen` forbidden, matches reviewed public JSON, and validates five rows/six grids/54 scenarios. Invalid step values exit 2 before creating an output directory.
- Restoration is idempotent on an independently authored fixture, refuses changed data and rejects hash corruption. Actual clean-clone restoration reconstructs the 34 large SEC sources; manifest tests verify all 67 public responses.
- Additional regressions reprice valid STRC inputs at $25/$250 and verify their yields against independent cash-flow PV; numeric provenance fields must exit 2 before writes.
- Portable input tests reject malformed schemas, missing instruments, wrong currencies, booleans/nonfinite/nonpositive prices, zero volatility, synthetic observation dates and future observations. User dates remain separate from retrieval timestamps. A custom-input CLI run with MSTR 300 changes the central value for all six notes while remaining offline. Impossible STRK option adjustments fail explicitly.

- Valuation-date tests run the CLI on the synthetic October 22 example with a rates file and check that the 30-year benchmark and spreads come from that file and that its hash is recorded. A later date without `--rates` exits 2 before writing, with a message naming the fix. Rates files reject percent-unit values, a missing 30-year tenor, mismatched dates, unknown keys, synthetic observation dates and future observations; dates before the terms snapshot or on a note's maturity are rejected. User marks dated October 22 run through diagnostics.
- Exchange-close tests load the default Nasdaq close file and reject a close dated before the valuation date, a close without its response SHA-256, a null preferred price without an `unavailable` reason and a null MSTR price. The default build excludes STRE with its last-trade date and keeps every other price dated October 21, 2026; diagnostics flag STRE as `stale_observation` and `no_observed_price`.
- Per-note volatility/spread inputs equal a direct tree price at those values, leave all nine grid values unchanged, and reject percent units and unknown notes. The terminal summary and the README preferred table are generated from the results; a test and CI check that the README table matches `results/preferred.json`.

CI pins immutable checkout/setup-python commits, Python 3.13.15 and NumPy 2.5.4. It uses `contents: read`, no persisted checkout credentials, a ten-minute timeout, restoration, the full offline suite, Python compilation and figure reproduction. No static typechecker is configured in this Python project. No schedules, paid services or deployment run.

## Figure checks

`figures/preferred-yields.svg` (the README hero) is generated from `results/preferred.json` by `scripts/render_yields.py`; CI fails if it drifts. Bars start at 0% and share one scale, so bar length is proportional to yield. It was rendered with `rsvg-convert` at 1,520px and 400px and inspected without clipping. Its figure brief passes `check_figure.py` with an accepted 14.7px minimum label at 400px and an agent-only reader test. The yellow STRD bar has 1.24:1 contrast against the surface, so it carries a charcoal outline and a bold direct label as DESIGN.md requires.

The scenario SVG is generated directly from the public scenario JSON. T3 headless previews at 760px and 400px were inspected without clipping or console errors. The figure-brief check passes, with accepted small-format label warnings and an explicitly weaker agent reader test. Minimum text contrast is 6.92:1. IBM Plex Sans/Anton are not installed on this Linux host; the portable SVG uses Arial/sans-serif fallback. No external fonts/images are vendored.

## Limits

These checks do not certify legal contract fidelity, security, vendor access rights, crash-atomic multi-file persistence or external production/PDE equivalence. Default prices are single-day exchange closes, not calibrated or live prices; option volatilities are assumptions. Full record-date ownership, 30/360 calendars, path-dependent triggers, make-whole tables, settlement elections and TF recovery remain out of scope. The comparison cannot isolate a noncumulative discount or fit a term structure.

Remote/default-branch, fresh-clone and hosted CI evidence appears in [publication](publication.md).
