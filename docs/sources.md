# Source coverage and dates

Purpose: trace financial observations and model inputs to primary evidence.

Research cutoff: October 21, 2026, America/Detroit. Retrieval timestamps remain independent of observation dates; some are October 22 UTC, the same local evening. The public URL/retrieval/SHA-256 ledger `data/raw/manifest.csv` contains **67 SEC and official-statistics responses**. Larger SEC originals restore from verified compressed parts. This public snapshot is separate from the preserved private v1 history/cache. Quote-presence tests validate extraction provenance, not every legal interpretation.

## Convertible offerings

The six offering 8-Ks and their indenture exhibits provide coupon dates, maturity, calls, puts, contingent conversion and settlement terms. Current principal, maximum conversion shares and Level 2 fair values use the [June 30, 2026 10-Q](https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm). The fair values are June 30 marks, not October prices.

- 2028: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312524222462/d887785d8k.htm); instrument extraction in `data/termsheets/convertibles/2028.json`.
- 2029: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312524263404/d905221d8k.htm); instrument extraction in `data/termsheets/convertibles/2029.json`.
- 2030A: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312524064321/d749312d8k.htm); instrument extraction in `data/termsheets/convertibles/2030A.json`.
- 2030B: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312525032800/d851880d8k.htm); instrument extraction in `data/termsheets/convertibles/2030B.json`.
- 2031: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312524070793/d792323d8k.htm); instrument extraction in `data/termsheets/convertibles/2031.json`.
- 2032: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312524164009/d857957d8k.htm); instrument extraction in `data/termsheets/convertibles/2032.json`.

The issuer [July 11, 2024 split announcement](https://www.strategy.com/press/microstrategy-announces-10-for-1-stock-split_07-11-2024) explicitly declares 10:1, with split-adjusted trading expected August 8. Original 2030A 0.6677, 2031 0.4297 and 2032 0.4894 shares per $1,000 become 6.677, 4.297 and 4.894. Q2 2026 maximum shares/principal independently reconcile those ratios. Later-issued notes need no further scaling. The 2031 maximum-share count introduces a tiny rounding residual. `data/termsheets/stock_split.json` records the manual browser extraction; direct Python retrieval of that issuer page returned 403, so no raw response hash is claimed for it. The original partial notes are preserved with this follow-up correction.

## Preferred offerings and amendments

- STRK: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312525020868/d791994d8k.htm); sourced designation fields in `data/termsheets/preferreds/STRK.json`.
- STRF: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312525062523/d943742d8k.htm); sourced designation fields in `data/termsheets/preferreds/STRF.json`.
- STRD: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312525138477/d941529d8k.htm); sourced designation fields in `data/termsheets/preferreds/STRD.json`.
- STRC: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312525167987/d43815d8k.htm); sourced designation fields in `data/termsheets/preferreds/STRC.json`.
- STRE: [offering 8-K](https://www.sec.gov/Archives/edgar/data/1050446/000119312525280178/d205736d8k.htm); sourced designation fields in `data/termsheets/preferreds/STRE.json`.

STRC's March 23 and June 30, 2026 amendments and October 15 rate notice supplement its original designation. Each field names its cached filing and excerpt. [October 5 proxy](https://www.sec.gov/Archives/edgar/data/1050446/000119312526413159/d503578ddef14a.htm) is a proposal for the October 28 meeting. It is not evidence of enactment. Pre-vote payment frequency is quarterly for STRF/STRE/STRK/STRD and semi-monthly for STRC.

## Public market assumptions and official rates

`data/market/2026-10-21/closes.json` holds the October 21, 2026 Nasdaq daily closes for MSTR ($153.48), STRF ($103.42), STRC ($99.20), STRK ($73.00) and STRD ($70.50) from Nasdaq's historical-quote API (`api.nasdaq.com/api/quote/<ticker>/historical`), retrieved October 22, 2026 UTC. Each entry records the request URL, retrieval time, byte count and SHA-256 of the response, and a Yahoo Finance daily-bar cross-check that agrees to the cent. The closing prices are published; the response bodies are not. Both generated result files identify `exchange_close` and the input-file SHA-256. `data/scenarios/market-inputs.json` keeps independently authored synthetic prices as a test and teaching example. The [input contract](market-inputs.md) supports authorized user-supplied observations without a provider-data dependency in CI.

US Treasury par yields, NY Fed SOFR and ECB AAA EUR spot/reference FX are attributed official statistics with individual observation/retrieval dates and original hashes. **Source: ECB statistics.** Original ECB bytes/metadata remain unchanged; effective-yield, FX and interpolation calculations are this project's transformations. The [ESCB reuse policy](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html) permits reuse of public statistics with attribution. Their inclusion does not transfer ownership or cover third-party data.

No Nasdaq, Cboe or Yahoo response bodies are published, compressed or otherwise. The archived private market histories and their ledger rows are omitted; only the October 21 closes above, with their response hashes, are public. The [Cboe website terms](https://www.cboe.com/terms/) and [Nasdaq legal terms](https://www.nasdaq.com/legal) do not establish unrestricted public redistribution permission. The complete original cache and its original Git history stay local/private; they are not ancestors of public `main`. No claim is made that those archived originals can be downloaded from this repository.

## STRE and contract follow-up

The [STRE issuer page](https://www.strategy.com/stre) describes an indicative market-maker midpoint. The [LuxSE issuer page](https://www.luxse.com/issuer/Strategy/122905) was also checked, but the retrieved pages supplied no usable dated numeric quote for this snapshot. Search-index recency is not an observation date. The original private v1 used the November 6, 2025 €80 offering price, not a current quote. Yahoo Finance's STRE.LU daily bars, fetched October 22, 2026, show the last bar with traded volume on January 29, 2026 at €84.80 (5,200 shares); every later bar repeats that price on zero volume. The public demo therefore gives STRE a null price and excludes it rather than substituting an old or authored value.

**Dated recheck, 2026-10-24.** The same Yahoo STRE.LU daily series, fetched again on October 24, 2026 UTC (bars from 2026-01-22 to 2026-10-23, 197 rows), gives the same result. The last bar with traded volume is 2026-01-29 (EUR 84.80, 5,200 shares). The 191 later bars with a close show EUR 84.80 on zero volume, including the 2026-10-21 valuation date, and one bar has no values. The exclusion therefore still holds. The limit is that this is one secondary source. The recheck did not query the Luxembourg Stock Exchange or a market maker, and the fetch is not stored in the repository.

The [2031 indenture](https://www.sec.gov/Archives/edgar/data/1050446/000119312524070793/d792323dex41.htm), sections 2.03 and 15.01, supports coupon entitlement at the September 15, 2028 repurchase date. Put cash entitlement now uses the contractual date before grid snapping. Exact record-date ownership and 30/360 accrual remain model limitations.

Public SEC filings/exhibits are attributed research evidence, not claimed as project-owned material or blanket public-domain content. Government/statistics sources retain their applicable notices. No paid feed, private account data, private hub data, access credentials or personal financial records are included. No code license is chosen.

## Storage and verification

`freeze_sources.py` only accepts the ledger's SEC/official-statistics host allowlist, verifies hashes and packs 34 large SEC files into <=16 KB chunks. `restore_data.py` checks original-byte hashes and refuses to overwrite changed sources. Public term sheets remain split by instrument; staged files stay within the 5,000-token limit. No vendor response body is hidden inside the compressed public archive.
