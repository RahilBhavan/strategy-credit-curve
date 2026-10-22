"""Strategy convertible notes: dated terms from the indentures, current figures parsed from the Q2 2026 10-Q."""
import datetime as dt
import functools
import json
import pathlib
import re

from .convertible import Convertible
from .text import html_to_text, squash

ROOT = pathlib.Path(__file__).resolve().parents[1]
TENQ = "data/raw/edgar/000105044626000044/mstr-20260630.htm"
TENQ_URL = "https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm"
NAMES = ("2028", "2029", "2030A", "2030B", "2031", "2032")


@functools.lru_cache(None)
def termsheet():
    return {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "data/termsheets/convertibles").glob("*.json"))}


@functools.lru_cache(None)
def tenq_text():
    return squash(html_to_text((ROOT / TENQ).read_bytes()))


def parse_10q():
    """Principal, carrying value, Level 2 fair value ($ thousands) and max conversion shares per note."""
    t = tenq_text()
    out = {}
    for n in NAMES:
        m = re.search(rf"{n} Convertible Notes \| \$? ?\|? ?([\d,]+) \| \$? ?\|? ?\( ([\d,]+) \) \| \$? ?\|? ?([\d,]+) \| \$? ?\|? ?([\d,]+) \| Level 2", t)
        s = re.search(rf"{n} Convertible Notes: ([\d,]+) shares of class A common stock", t)
        if not (m and s):
            raise ValueError(f"10-Q row not found for {n}")
        num = lambda x: int(x.replace(",", ""))
        out[n] = {"principal_k": num(m.group(1)), "unamortized_cost_k": num(m.group(2)),
                  "carrying_k": num(m.group(3)), "fair_value_k": num(m.group(4)),
                  "max_shares": num(s.group(1))}
        out[n]["ratio_per_1000"] = out[n]["max_shares"] / out[n]["principal_k"]
        out[n]["fair_price_pct"] = 100 * out[n]["fair_value_k"] / out[n]["principal_k"]
    return out


def _d(s):
    return dt.date.fromisoformat(s)


def _coupon_dates(mmdd, start, end):
    ds = []
    for y in range(start.year, end.year + 1):
        for md in mmdd:
            d = dt.date(y, int(md[:2]), int(md[3:]))
            if start < d <= end:
                ds.append(d)
    return sorted(ds)


def terms(name):
    """Dated terms for one note, every field taken from the term sheet (with its filing quote)."""
    ts = termsheet()[name]
    v = lambda k: ts[k]["value"]
    q = parse_10q()[name]
    return {
        "name": name,
        "term_source": f"data/termsheets/convertibles/{name}.json",
        "current_terms_as_of": "2026-06-30",
        "current_terms_source_url": TENQ_URL,
        "principal": q["principal_k"] * 1000,
        "coupon": v("coupon_rate"),
        "coupon_mmdd": v("interest_payment_dates"),
        "maturity": _d(v("maturity_date")),
        "ratio": q["ratio_per_1000"],
        "conversion_price": 1000 / q["ratio_per_1000"],
        "call_from": _d(v("call_protection_until")),
        "put_date": _d(v("holder_put_date")),
        "free_convert": _d(v("free_convertibility_date")),
        "fair_value_2026_06_30_pct": q["fair_price_pct"],
    }


def years(a, b):
    return (b - a).days / 365.0


def to_convertible(name, val_date):
    """Convertible (per $1,000) seen from ``val_date``; dates become year fractions."""
    t = terms(name)
    cds = _coupon_dates(t["coupon_mmdd"], val_date, t["maturity"]) if t["coupon"] else []
    puts = ((years(val_date, t["put_date"]), 1000.0),) if t["put_date"] > val_date else ()
    return Convertible(
        face=1000.0, maturity=years(val_date, t["maturity"]), ratio=t["ratio"],
        coupon_rate=t["coupon"], coupon_times=tuple(years(val_date, d) for d in cds),
        call_start=max(0.0, years(val_date, t["call_from"])), call_price=1000.0, call_trigger=1.3,
        puts=puts, free_convert=max(0.0, years(val_date, t["free_convert"])), coco_trigger=1.3)
