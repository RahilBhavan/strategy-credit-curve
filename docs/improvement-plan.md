# Market-input diagnostics slice

Authorized scope: preserve the offline October 21, 2026 contract/rate snapshot and synthetic defaults; add a reproducible, local-only way to inspect supplied market inputs and compare note marks with existing TF assumptions. Initial checkout: clean, main at 2f1959d. No glossary or ADR directory exists in this repository; docs/spec.md and docs/methodology.md own the terminology and decisions.

Done conditions:

1. A separate CLI emits deterministic JSON with each input's provenance, age in calendar days relative to the frozen valuation date, missing/stale/synthetic reasons, and no live-verification claim. A strict flag exits nonzero on incomplete coverage while retaining the diagnostic report.
2. Optional local note marks identify a supported note, USD per $1,000 face, full (dirty) price, valuation-date basis and dated source. Only same-date, attributed user marks and MSTR spot can produce model-minus-supplied differences for the nine explicit vol/spread assumptions. Missing or stale marks/dependencies produce null comparisons and reasons, never substituted offering/fair values.
3. Invalid prices, units, dates, retrieval ordering, duplicate JSON keys and ambiguous price bases fail before output. Schema-v1 public assumptions and their numeric reference results stay unchanged.
4. Tests exercise valid comparisons, missing/stale dependencies, malformed files, strict exit status, offline repeatability and unchanged model scenarios. Documentation provides a five-minute synthetic test example, source-access findings and measured limits.
5. Commit only this repo's changes, push the existing main branch through its restrictions, inspect CI and report its actual status.

Non-goals: live feeds, verified STRE observations, fitted spreads/credit curves, new UI/figures, contract/calendar changes, vendor body redistribution, licenses, private-archive access or other repositories.
