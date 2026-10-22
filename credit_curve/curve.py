"""Strategy preferred comparison using explicit market scenarios dated 2026-10-21.

Each preferred's yield is compared with a benchmark of matching currency and rate type:
fixed-rate USD perpetuals against the 30-year Treasury par yield, STRC (variable rate, reset by
management with a One-Month Term SOFR floor) against SOFR and the 30-year, STRE (EUR) against the
ECB 30-year AAA euro-area spot rate. All yields are effective annual rates so that payment
frequency (quarterly, or semi-monthly for STRC) and benchmark compounding do not distort spreads.
"""
import functools
import json
import pathlib

from . import inputs as market_inputs, market, preferred

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Finite horizons stand in for the perpetual conversion right, not observed maturities.
STRK_OPTION_YEARS = (5.0, 10.0, 20.0)
STRK_BASE_YEARS = 10.0


@functools.lru_cache(None)
def termsheet():
    return {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "data/termsheets/preferreds").glob("*.json"))}


def instruments():
    """Five rows in seniority order, every field drawn from the encoded term sheet."""
    ts = termsheet()
    order = ts["seniority"]["order"]["value"]
    rows = []
    for rank, tk in enumerate(order, start=1):
        t = ts[tk]
        rate = t["current_rate_latest_8k"]["value"] if tk == "STRC" else t["dividend_rate"]["value"]
        freq = 24 if tk == "STRC" else 4
        stated = t["stated_amount"]["value"]
        rows.append({
            "ticker": tk, "rank": rank, "currency": stated["currency"], "stated": stated["amount"],
            "rate": rate, "payments_per_year": freq, "annual_dividend": rate * stated["amount"],
            "cumulative": t["cumulative"]["value"],
            "convertible": tk == "STRK",
            "conversion_rate": t["conversion_rate"]["value"]["rate"] if tk == "STRK" else None,
            "conversion_price": t["conversion_rate"]["value"]["conversion_price"] if tk == "STRK" else None,
            "optional_call": t["optional_redemption"]["value"],
            "tax_redemption": t["tax_redemption"]["value"],
            "fundamental_change_put": t["fundamental_change_repurchase"]["value"],
            "term_source": f"data/termsheets/preferreds/{tk}.json",
            "listing": t["listing"]["value"],
        })
    return rows


def benchmarks():
    curve, csrc = market.treasury_curve()
    s, ssrc = market.sofr()
    e30, esrc = market.ecb_aaa_spot("30Y")
    fx, fxsrc = market.eurusd()
    return {
        "ust30": {"bey": curve[30], "effective": preferred.bey_to_effective(curve[30]), "source": csrc},
        "ust10": {"bey": curve[10], "effective": preferred.bey_to_effective(curve[10]), "source": csrc},
        "sofr": {"rate": s, "effective": (1 + s / 360 * 365 / 12) ** 12 - 1, "source": ssrc},
        "eur30": {"cc": e30, "effective": preferred.cc_to_effective(e30), "source": esrc},
        "eurusd": {"rate": fx, "source": fxsrc},
        "curve": curve,
    }


def strk_option(spot, rate_curve, inputs):
    vols = inputs['strk_option_volatility']
    grid = {}
    for T in STRK_OPTION_YEARS:
        r = market.cc_rate(market.interp(rate_curve, T))
        for label in ('base', 'sensitivity'):
            grid[f'{label}_{T:g}y'] = preferred.conversion_option(spot, 0.1, 1000.0, T, r, vols[label])
    return {'volatility_inputs': vols, 'values': grid,
            'base': grid[f'base_{STRK_BASE_YEARS:g}y']}


def build(inputs=None):
    inputs = market_inputs.load() if inputs is None else inputs
    b = benchmarks()
    mstr = market_inputs.quote(inputs, "MSTR")
    rows = instruments()
    for row in rows:
        tk = row["ticker"]
        q = market_inputs.quote(inputs, tk)
        row['price'] = q['price']
        row['price_source'] = q['source']
        row['price_is_synthetic'] = inputs['kind'] == 'synthetic_scenario'
        observation = q['source']['as_of']
        row['price_is_stale'] = None if observation is None else observation < inputs['valuation_date']
        row['live_ranking_eligible'] = False  # No supplied file is independently verified as a live feed.
        if tk == 'STRE':
            fx = b['eurusd']['rate']
            row['usd_price_at_reference_fx'] = row['price'] * fx
            row['usd_annual_dividend_at_reference_fx'] = row['annual_dividend'] * fx
            row['fx_only_usd_return_scenarios'] = {str(change): change for change in (-0.2, 0.0, 0.2)}
            row['fx_scenario_assumption'] = 'EUR scenario price held fixed; unhedged USD principal return only; no dividends'
        P, D, m = row["price"], row["annual_dividend"], row["payments_per_year"]
        row["current_yield"] = preferred.current_yield(D, P)
        row["effective_yield"] = preferred.effective_annual(D, P, m)
        if tk == "STRE":
            row["benchmark"] = "ECB AAA euro-area 30y spot"
            row["benchmark_effective"] = b["eur30"]["effective"]
        else:
            row["benchmark"] = "UST 30y par"
            row["benchmark_effective"] = b["ust30"]["effective"]
        row["spread_bp"] = 1e4 * (row["effective_yield"] - row["benchmark_effective"])
        if tk == "STRC":
            row["spread_vs_sofr_bp"] = 1e4 * (row["effective_yield"] - b["sofr"]["effective"])
            # optional redemption at $101: a call only raises the return when bought below 101,
            # report one-year yield-to-call for scale; this is not a full yield-to-worst search
            row["ytc_1y_at_101"] = preferred.yield_to_call(P, D, m, 1.0, 101.0)
            row["min_perpetual_and_1y_call_scenario"] = min(row["effective_yield"], row["ytc_1y_at_101"])
        else:
            row["ytc_1y_at_101"] = None
            row["min_perpetual_and_1y_call_scenario"] = row["effective_yield"]
    strk = next(r for r in rows if r["ticker"] == "STRK")
    opt = strk_option(mstr["price"], b["curve"], inputs)
    strk["option"] = opt
    strk["option_value"] = opt["base"]
    strk["straight_price"] = strk["price"] - opt["base"]
    if any(v >= strk["price"] for v in opt["values"].values()):
        raise ValueError("STRK option scenario leaves a nonpositive straight-price proxy; change input assumptions")
    strk["straight_effective_yield"] = preferred.effective_annual(strk["annual_dividend"], strk["straight_price"], 4)
    strk["straight_spread_bp"] = 1e4 * (strk["straight_effective_yield"] - strk["benchmark_effective"])
    strk["straight_spread_range_bp"] = sorted(
        1e4 * (preferred.effective_annual(8.0, strk["price"] - v, 4) - strk["benchmark_effective"])
        for v in opt["values"].values())[::len(opt["values"]) - 1]
    return {"as_of": "2026-10-21", "market_inputs": market_inputs.provenance(inputs), "kind": "heterogeneous_perpetual_comparison_not_credit_term_structure",
            "daily_dividend_amendment": "pending Oct 28 vote; not enacted as of Oct 21", "mstr": mstr, "benchmarks": {k: v for k, v in b.items() if k != "curve"},
            "rows": rows, "strd": strd_discount(rows)}


def strd_discount(rows):
    """Input-dependent adjacent spread gap, with no causal identification."""
    by = {r["ticker"]: r for r in rows}
    return {
        "adjacent_strd_minus_strk_scenario_spread_bp":
            by["STRD"]["spread_bp"] - by["STRK"]["straight_spread_bp"],
        "interpretation": "Descriptive gap only. Seniority, conversion-option assumptions, liquidity, "
                          "call rights and cumulative status differ. No isolated noncumulative premium.",
    }
