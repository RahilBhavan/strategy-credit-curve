# Verification record

Purpose: record tested public behavior, distinct from source observations and model assumptions.

## Reproduction

Use the README commands: install `numpy==2.5.4`, run `scripts/restore_data.py`, run `python -m unittest discover -s tests -v`, then `python -m credit_curve.run` and `python scripts/render_results.py`. The suite passes **36 tests** with Python 3.13.15 and 3.14.7. No provider credentials are used. Tests/demo use no network after package installation.

The default CLI emits five preferred rows and six nine-scenario grids using **synthetic** market inputs. It records kind, valuation date, input-file hash and per-input observation/retrieval provenance. Public outputs and the SVG are deterministic in the exercised environments. The figure shows grid extrema, not confidence intervals.

## Evidence exercised

- The 22 original numerical/source tests continue, adapted to the public input labels and public-source ledger. They cover split reconciliation, filing quotations, all public-source hashes, independent no-credit and positive-credit European TF limits, bond PV, convergence, calls, puts and invalid pricing inputs.
- A regression for an off-grid coupon-date put failed before the fix ($955.9974818331 against analytic $965.5574566514) and passes after it. Contractual-date cash entitlement now survives grid snapping.
- Mocked 429 retry/success writes one verified response and reuses the cache; exhausted 503 retries leave the previous body/manifest unchanged. Failed source acquisition returns exit status 1.
- The real CLI runs twice with `urlopen` forbidden, matches reviewed public JSON, and validates five rows/six grids/54 scenarios. Invalid step values exit 2 before creating an output directory.
- Restoration is idempotent on an independently authored fixture, refuses changed data and rejects hash corruption. Actual clean-clone restoration reconstructs the 34 large SEC sources; manifest tests verify all 67 public responses.
- Portable input tests reject malformed schemas, missing instruments, wrong currencies, booleans/nonfinite/nonpositive prices, zero volatility, synthetic observation dates and future observations. User dates remain separate from retrieval timestamps. A custom-input CLI run with MSTR 300 changes the central value for all six notes while remaining offline. Impossible STRK option adjustments fail explicitly.

CI pins immutable checkout/setup-python commits, Python 3.13.15 and NumPy 2.5.4. It uses `contents: read`, no persisted checkout credentials, a ten-minute timeout, restoration, the full offline suite, Python compilation and figure reproduction. No static typechecker is configured in this Python project. No schedules, paid services or deployment run.

## Figure checks

The SVG is generated directly from the public scenario JSON. T3 headless previews at 760px and 400px were inspected without clipping or console errors. The figure-brief check passes, with accepted small-format label warnings and an explicitly weaker agent reader test. Minimum text contrast is 6.92:1. IBM Plex Sans/Anton are not installed on this Linux host; the portable SVG uses Arial/sans-serif fallback. No external fonts/images are vendored.

## Limits

These checks do not certify legal contract fidelity, security, vendor access rights, crash-atomic multi-file persistence or external production/PDE equivalence. Default public inputs are synthetic, not calibrated prices. Full record-date ownership, 30/360 calendars, path-dependent triggers, make-whole tables, settlement elections and TF recovery remain out of scope. The comparison cannot isolate a noncumulative discount or fit a term structure.

Remote/default-branch, fresh-clone and hosted CI evidence appears in [publication](publication.md).
