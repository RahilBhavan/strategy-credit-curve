# Publication receipt

Status: sanitized checkout prepared; remote publication verification pending.

Target: https://github.com/RahilBhavan/strategy-credit-curve, public `main`.

The user authorized a clean publication snapshot. Original v1 commits (`49f5d83`, `c016da8`) and reviewed local fixes remain in the original local project history/cache, privately. The public history begins separately and does not reference those commits or any private backup refs/tags. No force push or existing remote history replacement is used.

The public snapshot contains reviewed source, all five preferreds/six notes, 67 attributed SEC/official-statistics responses (34 large SEC files compressed in verified chunks), validated user-supplied market-input support and an explicitly synthetic default scenario. It contains no full Nasdaq/Cboe/Yahoo responses, archived originals or original vendor-ledger rows. No license file yet.

Local proof before publication: 36 offline tests pass. Default and custom-input CLI paths retain all 54 convertible scenarios; invalid inputs are rejected before output writes. See [verification](verification.md) for numerical/retry/persistence evidence. Hosted CI and fresh remote clone evidence will be appended after the first push.

## Canonical checkout and private preservation

Canonical public checkout: `~/projects/strategy-credit-curve`, branch `main`, upstream `origin/main`. The public history starts at `466c2f099607d4b07c6a1b2ba73686c617315ece`. The original project history/cache was copied intact to `~/.local/share/strategy-credit-curve-private/original-v1` before switching the canonical workspace. That private backup has no remotes or branch upstreams and uses `push.default=nothing`. Original refs remain locally named `private/original-v1`, without a public upstream. No private backup refs or tags are pushed. Ordinary pushes from the canonical project are restricted by `remote.origin.push=refs/heads/main:refs/heads/main`.

Initial remote clone `466c2f0` restored all 34 packed sources, passed its then-current 36 tests on a fresh Python 3.14.7 environment, ran the full demo and reproduced both outputs/figure. Parent independently repeated this snapshot check. Initial hosted CI run [39719643468](https://github.com/RahilBhavan/strategy-credit-curve/actions/runs/39719643468) exposed an overly strict cross-runtime exact-float reference assertion; the repaired test retains byte-exact same-machine repeats and documents narrow numerical tolerances. Hosted verification of the repair remains pending.
