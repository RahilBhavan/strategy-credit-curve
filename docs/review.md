# Correctness and source review

Scope: the existing v1 at `c016da8`, preserving its source corpus and architecture. Baseline: 22 passing tests in the documented scratch environment; no uncommitted user work. Seven passes covered correctness, error handling, security, accessibility, performance, dead code and repository conventions. Accessibility was limited to the plain CLI/help and generated figure, with no application UI. No demonstrated performance, dead-code or convention bug survived verification. This is a focused research-code review, not a security certification.

## Fixed and proven

1. **Coupon-date put entitlement was lost after grid rounding.** `credit_curve/convertible.py` replaced coupon-inclusive continuation with principal plus interest recomputed at the rounded node. For face $1,000, coupon 2%, coupon/put at year 0.49 and a two-step one-year tree, that erased a $10 coupon. The new regression failed at $955.9974818331 against the analytic $965.5574566514. Put payoff now freezes accrued entitlement at its contractual date before grid snapping; the regression passes. The sourced 2031 September 15, 2028 put is on a coupon date. All six scenario grids were regenerated; public results were then regenerated again using the explicitly synthetic publication inputs. Exact record-date ownership remains a disclosed limitation.
2. **Failed downloads returned process success.** `credit_curve/market_fetch.py` printed `FAIL` for a failed source and returned normally. A mocked failed source reproduced `None` rather than a failure status. It now returns 1 if any source fails and passes that status to `sys.exit`. The regression and full suite pass. Existing caches remain untouched when HTTP retries exhaust.

The independent T3 reviewer was read-only and identified the first failure. Parent reproduced it and made the repair. Task ID: `node:delegated-task:command%3Amcp%3A8142576d-8450-4c67-b152-27d45a55929c%3Adelegate-task%3Astrategy-credit-curve-review-1`. No second review round or nested delegation was used.

## Evidence and discarded candidates

Quote-presence and split tests support extraction provenance, not full legal fidelity. Six current ratios reconcile with the original terms and 10:1 split. The five preferred classifications, STRE FX arithmetic and pending October 28 proposal status produced no new demonstrated failure. Finite STRK option horizons, dated fair values, par-rate proxies and node-based call/conversion conditions are disclosed assumptions rather than secretly calibrated observations. STRE remains stale; the primary-page follow-up supplied no usable dated quote.

The fetcher's internal paths are constructed by trusted source-fetch code; no untrusted file-upload or network service surface exists. Snapshot restoration already checks output-path containment and hashes. No exploitable path-input candidate was retained. Existing raw public filings contain issuer contacts and corporate identifiers, which are source evidence, not user identity material.

## Checks and limits

After both fixes and portable input support, all 36 tests pass on Python 3.13.15 and 3.14.7 with NumPy 2.5.4. New tests cover behavior, not just compilation. Modified functions and direct callers were reread; the final diff was reviewed. The public result changes also reflect the documented switch to synthetic market inputs, rather than an updated market observation.

The accrual routine still idealizes half-year periods; full 30/360 day counts, record-date ownership, path-dependent triggers, make-whole tables, settlement elections and an external production TF/PDE comparison remain unimplemented. The comparison cannot isolate a noncumulative discount or supply a fitted term structure. Those limits are prominent in the README/methodology.

Next: use the verified offline snapshot and documented assumptions when interpreting the published results.
