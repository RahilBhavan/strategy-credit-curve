# Methodology

Purpose: distinguish observed terms from the comparison and pricing assumptions.

## Preferred comparison

The encoded seniority order is STRF > STRC > STRE > STRK > STRD. STRD is noncumulative; the other four accumulate unpaid dividends under their terms. These rights do not imply dividends will be paid. Current yield is annual stated dividend / price. The effective yield compounds that ratio at the stated frequency, assuming reinvestment and a constant dividend rate. STRC's management-set variable rate is held at 12% and its pre-vote semi-monthly schedule is retained. Overnight SOFR is a comparison benchmark, not the contractual CME one-month Term SOFR floor.

Fixed USD issues use a 30-year Treasury par-yield proxy; STRE uses ECB 30-year AAA EUR spot. All benchmarks are converted to effective annual units before subtraction, but this does not remove their economic differences. STRE has no public price here: its last Luxembourg Stock Exchange bar with traded volume is January 29, 2026, so the row is excluded and no yield is computed. USD-equivalent STRE price/dividend use the dated ECB FX reference. The ±20% FX-only principal returns assume unchanged EUR price; they are hypothetical, without reinvestment, costs or dividends.

STRK's holder conversion right is approximated as 0.1 European MSTR calls at a $1,000 strike, for assumed 5/10/20-year horizons and two explicit input volatility proxies. The public volatility proxies are authored assumptions; users may supply their own authorized observations. A perpetual conversion right is not a European option, and the observed IV maturities do not extend to those horizons. Subtracting this assumed option value yields a scenario straight-price proxy. It is not an option-adjusted spread calibrated to a joint preferred/equity model.

Earlier private code fitted spread to ordinal seniority and attributed the residual to noncumulative status. That attribution is removed: the tiny heterogeneous cross-section cannot identify a causal premium. The adjacent STRD–STRK scenario gap is descriptive only.

## Convertible tree

TF discounts cash-only continuation at r + assumed spread and equity continuation at r. Exercise transfers value to the relevant component. Coupons are semiannual, ACT/365 times mapped to nearby grid points; holder puts and issuer calls are simplified dated barriers. Put cash entitlement uses the contractual put date before snapping to the grid, so a coupon-date put retains that coupon. Par curves are interpolated by tenor and converted to continuous rates; there is no discount-factor bootstrap. The public spot is the October 21, 2026 Nasdaq MSTR close; government rates use the frozen October 21 research snapshot unless a dated rates file is supplied. User-supplied spot and volatility inputs remain labeled with their own provenance. Volatility 40/60/80% and spread 2/5/10% are **assumptions**, not estimates of note-specific risk. Optional per-note volatility and spread inputs add one valuation per note at those values; they are the supplier's assumptions and do not replace the grid.

The 2030A/2031/2032 original conversion ratios predate the 2024 10:1 split. Current ratios come from maximum conversion shares / principal in thousands in the Q2 2026 filing. Never multiply those current ratios by 10 again. The 2031 ratio has tiny share-rounding error. See [sources](sources.md).

## Independent validation and limits

With no credit, coupon, call or early-exercise incentive, value equals discounted face plus a Black–Scholes call. With conversion disabled, it equals the risky coupon-bond PV. For **European-only conversion with positive spread**, terminal cash is face when S_T < K and equity is ratio × S_T otherwise. Independent lognormal integration gives:

`cash = face * exp(-(r+s)T) * N(-d2)`

`equity = ratio * S0 * exp(-qT) * N(d1)`

where `d1=(ln(S0/K)+(r-q+vol²/2)T)/(vol*sqrt(T))`, `d2=d1-vol*sqrt(T)` and `K=face/ratio`. The test constructs these directly with `erf`, rather than using the tree or its option helper. The odd/even averaged tree matches total value within $0.12 per $100 face and cash within $0.50 for the tested case. This validates a restricted positive-credit limit, not every American feature.

Additional convergence/put/call tests check numerical behavior. A retained three-step Hull hazard-model textbook regression gives 106.93; it is a **different model**, not an independent positive-credit TF benchmark. No external production convertible pricer or full PDE benchmark was exercised. [Milanov and Kounchev (2011)](https://arxiv.org/abs/1111.2683) discuss CRR/TF limitations; [their 2012 paper](https://arxiv.org/abs/1206.1400) develops a different equity-to-credit-risk framework. These caveats limit interpretation of both prices and deltas.

Accrued-interest interpolation uses an idealized half-year, rather than the indentures’ 30/360 convention. Coupon ownership across record dates and conversion/redemption is not represented separately. These are model limitations; the repaired put-date coupon entitlement is not a full event-calendar implementation.
