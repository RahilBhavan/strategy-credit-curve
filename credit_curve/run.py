"""Offline instrument comparison and six-note TF scenario CLI."""
import argparse
import datetime as dt
import json
import pathlib

from . import curve, inputs as market_inputs, market, notes, summary
from .convertible import price

ROOT = pathlib.Path(__file__).resolve().parents[1]


GRID_VOLS = (0.4, 0.6, 0.8)
GRID_SPREADS = (0.02, 0.05, 0.10)


def note_scenarios(steps=600, inputs=None):
    inputs = market_inputs.load() if inputs is None else inputs
    day = dt.date.fromisoformat(inputs["valuation_date"])
    spot = market_inputs.quote(inputs, "MSTR")["price"]
    yc = inputs["rates"]["ust_par_yield"]["tenors"]
    rows = []
    for name in notes.NAMES:
        t = notes.terms(name)
        if t["maturity"] <= day:
            raise ValueError(f"valuation_date {day} is on or after the {name} note maturity {t['maturity']}")
        cb = notes.to_convertible(name, day)
        r = market.cc_rate(market.interp(yc, cb.maturity))

        def scenario(vol, spread):
            v = price(cb, spot, vol, r, spread=spread, steps=steps)
            return {"vol_assumption": vol, "spread_assumption": spread,
                    "value_per_1000_usd": v.value, "cash_part_usd": v.cash_part,
                    "equity_part_usd": v.equity_part, "delta_shares": v.delta}

        vals = [scenario(vol, spread) for vol in GRID_VOLS for spread in GRID_SPREADS]
        supplied = inputs["note_assumptions"].get(name)
        if supplied is not None:
            supplied = {**scenario(supplied["volatility"], supplied["credit_spread"]), "source": supplied["source"]}
        rows.append({"terms": t, "risk_free_cc_proxy": r, "conversion_parity_per_1000_usd": t["ratio"] * spot,
                     "scenarios": vals, "supplied_assumption": supplied})
    return {"as_of": day, "market_inputs": market_inputs.provenance(inputs), "spot": spot, "spot_source": market_inputs.quote(inputs, "MSTR")["source"], "model": "CRR Tsiveriotis-Fernandes", "steps": steps,
            "interpretation": "Assumed vol/spread grid plus any supplied per-note assumption; model values, not fitted "
                              "prices or observed current note quotes. "
                              "June 30 Level 2 fair values in terms are stale context only.", "notes": rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "results")
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--market-input", type=pathlib.Path, default=market_inputs.DEFAULT,
                    help="schema-v1 input JSON; defaults to explicitly synthetic prices/volatilities")
    ap.add_argument("--rates", type=pathlib.Path,
                    help="schema-v1 benchmark-rate JSON for the input's valuation_date; "
                         "omit to use the bundled 2026-10-21 snapshot")
    args = ap.parse_args()
    if args.steps < 2 or args.steps > 10000:
        ap.error("steps must lie in [2,10000]")
    try:
        inputs = market_inputs.load(args.market_input, args.rates)
        preferred = curve.build(inputs)
        convertible = note_scenarios(args.steps, inputs)
    except (ValueError, KeyError, TypeError, OSError) as error:
        ap.error(str(error))
    args.out.mkdir(parents=True, exist_ok=True)
    # Compact nested JSON keeps each result file reviewable and below the file-size hook.
    (args.out / "preferred.json").write_text(json.dumps(preferred, separators=(",", ":"), allow_nan=False) + "\n")
    (args.out / "convertibles.json").write_text(json.dumps(convertible, default=str, separators=(",", ":"), allow_nan=False) + "\n")
    print(summary.render(preferred, convertible))
    priced = sum(r["price"] is not None for r in preferred["rows"])
    print(f"Wrote {priced} priced preferred comparisons ({len(preferred['rows']) - priced} excluded, no trade) "
          f"and six note scenario grids to {args.out}")


if __name__ == "__main__":
    main()
