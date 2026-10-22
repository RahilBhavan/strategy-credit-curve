"""Offline instrument comparison and six-note TF scenario CLI."""
import argparse
import datetime as dt
import json
import pathlib

from . import curve, inputs as market_inputs, market, notes
from .convertible import price

ROOT = pathlib.Path(__file__).resolve().parents[1]


def note_scenarios(steps=600, inputs=None):
    inputs = market_inputs.load() if inputs is None else inputs
    day = dt.date(2026, 10, 21)
    spot = market_inputs.quote(inputs, "MSTR")["price"]
    yc, _ = market.treasury_curve()
    rows = []
    for name in notes.NAMES:
        t = notes.terms(name)
        cb = notes.to_convertible(name, day)
        r = market.cc_rate(market.interp(yc, cb.maturity))
        vals = []
        for vol in (0.4, 0.6, 0.8):
            for spread in (0.02, 0.05, 0.10):
                v = price(cb, spot, vol, r, spread=spread, steps=steps)
                vals.append({"vol_assumption": vol, "spread_assumption": spread,
                             "value_per_1000_usd": v.value, "cash_part_usd": v.cash_part,
                             "equity_part_usd": v.equity_part, "delta_shares": v.delta})
        rows.append({"terms": t, "risk_free_cc_proxy": r, "scenarios": vals})
    return {"as_of": day, "market_inputs": market_inputs.provenance(inputs), "spot": spot, "spot_source": market_inputs.quote(inputs, "MSTR")["source"], "model": "CRR Tsiveriotis-Fernandes", "steps": steps,
            "interpretation": "Assumed vol/spread grid; not fitted prices or observed current note quotes. "
                              "June 30 Level 2 fair values in terms are stale context only.", "notes": rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path, default=ROOT / "results")
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--market-input", type=pathlib.Path, default=market_inputs.DEFAULT,
                    help="schema-v1 input JSON; defaults to explicitly synthetic prices/volatilities")
    args = ap.parse_args()
    if args.steps < 2 or args.steps > 10000:
        ap.error("steps must lie in [2,10000]")
    try:
        inputs = market_inputs.load(args.market_input)
        preferred = curve.build(inputs)
        convertible = note_scenarios(args.steps, inputs)
    except (ValueError, KeyError, TypeError, OSError) as error:
        ap.error(str(error))
    args.out.mkdir(parents=True, exist_ok=True)
    # Compact nested JSON keeps each result file reviewable and below the file-size hook.
    (args.out / "preferred.json").write_text(json.dumps(preferred, separators=(",", ":"), allow_nan=False) + "\n")
    (args.out / "convertibles.json").write_text(json.dumps(convertible, default=str, separators=(",", ":"), allow_nan=False) + "\n")
    print(f"Wrote five preferred comparisons and six note scenario grids to {args.out}")


if __name__ == "__main__":
    main()
