# Publication receipt

Status: **published and verified**, October 22, 2026. Financial terms/rate cutoff remains **October 21, 2026**; synthetic scenarios are not new market observations. The October 28 vote remains pending at that cutoff.

Repository: https://github.com/RahilBhavan/strategy-credit-curve (public, default branch `main`). Reviewed implementation commit: `73505a7f5201b71585a0acaec6bce635702710b5`. Public root commit: `466c2f099607d4b07c6a1b2ba73686c617315ece`. This receipt follows the verified implementation in a documentation-only commit; `git rev-parse HEAD` identifies the checked-out receipt revision.

## Verified evidence

- [Hosted CI run 39720178357](https://github.com/RahilBhavan/strategy-credit-curve/actions/runs/39720178357) passed all **39 tests**, Python compilation, public-source restoration and figure reproduction on pinned Python 3.13.15 / NumPy 2.5.4.
- A fresh GitHub clone installed pinned dependencies in a fresh Python 3.14.7 environment, restored **34 packed SEC sources**, passed the then-current 36 tests, ran the full offline demo and regenerated its outputs/figure exactly. The final 39-test suite and demo also passed from the canonical checkout; hosted CI exercises the final implementation. A final remote-clone confirmation follows the receipt commit.
- Demo: **five preferred rows, six note grids, 54 note scenarios**, with synthetic market prices/volatility and attributed contract/rate inputs. Custom-input tests change all six central note values and preserve source dates/hash metadata. Both JSON outputs are repeatable; schema/types/text/counts/array order stay exact, and cross-runtime saved floats use rtol 1e-12 / atol 1e-10. Analytic pricing invariants remain unchanged.
- All **67 public source responses** have SHA-256 provenance. Every packed file was reconstructed and checked against the SEC-only packing index. Full Nasdaq/Cboe/Yahoo bodies and their vendor-ledger rows are absent from every public ancestor. Credential-pattern and oversized-blob scans found no publication blocker; the largest initial public blob is 16,472 bytes. Private refs/tags were never pushed.
- Initial [CI run 39719643468](https://github.com/RahilBhavan/strategy-credit-curve/actions/runs/39719643468) caught a last-bit cross-runtime exact-float reference assertion. Same-machine repeat bytes remain strict; the corrected comparison reports actual/reference/delta by JSON path, and a regression rejects meaningful numeric/schema changes. Subsequent hosted CI is green.

## Canonical workspace and private backup

Canonical public path: `/home/rahil/projects/strategy-credit-curve` (`~/projects/strategy-credit-curve`). Normal checkout: `main`, upstream `origin/main`. `remote.origin.push=refs/heads/main:refs/heads/main` restricts ordinary pushes to public `main`; a plain `git push --dry-run` was checked successfully. No original-history branch is used as public upstream.

Private original path: `~/.local/share/strategy-credit-curve-private/original-v1`. It preserves the complete pre-publication checkout, original refs/history and **81-response original cache**. Its HEAD is `cc08097040abc45058885cda176e91d3bd71b063`, retaining original v1 `c016da8` and both reviewed fixes. This private backup has **no remotes or branch upstreams** and uses `push.default=nothing`. Its parent directory is mode 0700. A `PRIVATE-BACKUP.txt` labels its restricted material.

The canonical repository also retains local `private/original-v1` without a public upstream; its push remote is deliberately disabled. Never push backup refs, `--all`, `--mirror` or private tags. The sanitized public history is independent, created with the user's explicit authorization; no original history was rewritten and no force push occurred. Leftover vendor files in the public working tree were removed only after hash-matching the preserved private copies.

## Limits retained

This is a heterogeneous comparison, not a fitted credit term structure, isolated noncumulative premium, live ranking or calibration. STRE has no verified current quote. Public prices/option volatilities are synthetic; external data must be supplied locally under provider terms. Exact record-date ownership, 30/360 accrual, path-dependent triggers, make-whole tables, settlement elections and external production/PDE equivalence remain unimplemented. No license file yet; third-party ownership/notices remain applicable. No deployment, trades, private-account actions or recurring service was created.

## Update 2026-10-22: license

The MIT license was added in `LICENSE`. It covers this project's code only. Earlier statements in this record that no license file existed describe the state at publication.

## Update 2026-10-22: reader-test fixes

A cold-reader test found that later-dated user marks were rejected and the key outputs were hard to find. The CLI now accepts a user `valuation_date` with a validated rates file (`--rates`), optional per-note volatility/spread inputs, and prints a summary table; the README preferred table is generated from `results/preferred.json`. The October 21 snapshot remains the default, and its public numbers are unchanged. Hosted CI for the pushed commit is the verification record; see `git log` for the SHA.
