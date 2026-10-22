"""Parse cached market snapshots. Every value returned carries its source URL and as-of date."""
import csv, datetime as dt, io, json, math
from . import bs, fetch

SNAP = "2026-10-21"


def _src(rel, as_of, note=""):
    m = fetch.source(rel)
    return {"url": m["url"], "fetched_utc": m["fetched_utc"], "as_of": as_of, "file": f"data/raw/{rel}", "note": note}


def quote(ticker, day=SNAP):
    """Last sale from Nasdaq's quote API, cross-checked against Yahoo's daily close."""
    rel = f"market/{day}/nasdaq-{ticker}.json"
    p = json.loads(fetch.get(None, rel))["data"]["primaryData"]
    last = float(p["lastSalePrice"].replace("$", "").replace(",", ""))
    as_of = dt.datetime.strptime(p["lastTradeTimestamp"].replace("ET", "").strip()[:12].strip(), "%b %d, %Y").date().isoformat()
    return {"price": last, "currency": "USD", "source": _src(rel, as_of, "Nasdaq last sale (regular session close)")}


def yahoo_closes(ticker, day=SNAP, span="1y"):
    rel = f"market/{day}/yahoo-{ticker}-{span}.json"
    r = json.loads(fetch.get(None, rel))["chart"]["result"][0]
    out = {}
    for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]):
        if c is not None:
            out[dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat()] = c
    return out, _src(rel, max(out), "Yahoo Finance chart API daily closes")


def treasury_curve(day=SNAP, date=None):
    """Daily Treasury par yield curve (bond-equivalent, percent -> decimal) for ``date`` (default latest)."""
    rel = f"market/{day}/treasury-par-{(date or day)[:4]}.csv"
    rows = list(csv.DictReader(io.StringIO(fetch.get(None, rel).decode())))
    iso = lambda s: dt.datetime.strptime(s, "%m/%d/%Y").date().isoformat()
    row = next(r for r in rows if date is None or iso(r["Date"]) <= date)
    tenors = {"1 Mo": 1 / 12, "3 Mo": 0.25, "6 Mo": 0.5, "1 Yr": 1, "2 Yr": 2, "3 Yr": 3, "5 Yr": 5, "7 Yr": 7,
              "10 Yr": 10, "20 Yr": 20, "30 Yr": 30}
    curve = {t: float(row[k]) / 100 for k, t in tenors.items() if row.get(k)}
    return curve, _src(rel, iso(row["Date"]), "US Treasury daily par yield curve")


def realized_vol(closes, end, days=252):
    """Annualised close-to-close volatility over the ``days`` trading days ending on or before ``end``."""
    ks = [k for k in sorted(closes) if k <= end][-(days + 1):]
    lr = [math.log(closes[b] / closes[a]) for a, b in zip(ks, ks[1:])]
    mu = sum(lr) / len(lr)
    return math.sqrt(sum((x - mu) ** 2 for x in lr) / (len(lr) - 1) * 252), ks[0], ks[-1]


def close_on_or_before(closes, date):
    k = max(k for k in closes if k <= date)
    return closes[k], k


def interp(curve, t):
    ks = sorted(curve)
    if t <= ks[0]:
        return curve[ks[0]]
    if t >= ks[-1]:
        return curve[ks[-1]]
    for a, b in zip(ks, ks[1:]):
        if a <= t <= b:
            return curve[a] + (curve[b] - curve[a]) * (t - a) / (b - a)


def cc_rate(par_bey):
    """Semi-annual bond-equivalent yield to a continuously compounded rate."""
    return 2 * math.log(1 + par_bey / 2)


def sofr(day=SNAP):
    rel = f"market/{day}/sofr-last10.json"
    r = json.loads(fetch.get(None, rel))["refRates"][0]
    return r["percentRate"] / 100, _src(rel, r["effectiveDate"], "NY Fed SOFR")


def _ecb(rel):
    rows = list(csv.DictReader(io.StringIO(fetch.get(None, rel).decode())))
    r = rows[-1]
    return float(r["OBS_VALUE"]), r["TIME_PERIOD"]


def ecb_aaa_spot(tenor, day=SNAP):
    rel = f"market/{day}/ecb-aaa-spot-{tenor}.csv"
    v, d = _ecb(rel)
    return v / 100, _src(rel, d, f"ECB euro area AAA government spot rate, {tenor} (continuously compounded)")


def estr(day=SNAP):
    rel = f"market/{day}/ecb-estr.csv"
    v, d = _ecb(rel)
    return v / 100, _src(rel, d, "ECB euro short-term rate (EUR STR)")


def eurusd(day=SNAP):
    rel = f"market/{day}/ecb-eurusd.csv"
    v, d = _ecb(rel)
    return v, _src(rel, d, "ECB euro reference rate, USD per EUR")


def mstr_options(day=SNAP):
    """CBOE delayed MSTR option quotes -> list of (expiry, strike, mid, open_interest, cboe_iv)."""
    rel = f"market/{day}/cboe-MSTR-options.json"
    o = json.loads(fetch.get(None, rel))
    rows = []
    for x in o["data"]["options"]:
        s = x["option"]
        if s[10] != "C" or x["bid"] <= 0 or x["ask"] <= 0:
            continue
        exp = dt.date(2000 + int(s[4:6]), int(s[6:8]), int(s[8:10]))
        rows.append({"expiry": exp.isoformat(), "strike": int(s[11:]) / 1000, "mid": (x["bid"] + x["ask"]) / 2,
                     "bid": x["bid"], "ask": x["ask"], "oi": x["open_interest"], "cboe_iv": x["iv"]})
    return rows, o["data"]["close"], _src(rel, o["data"]["last_trade_time"][:10],
                                          f"CBOE delayed quotes, snapshot {o['timestamp']}")


def option_iv(expiry, strike, day=SNAP, val_date=SNAP):
    """Own Black-Scholes IV from the call mid nearest to ``strike`` at ``expiry`` (q = 0)."""
    rows, close, src = mstr_options(day)
    cands = [r for r in rows if r["expiry"] == expiry]
    if not cands:
        raise KeyError(expiry)
    r_ = min(cands, key=lambda r: abs(r["strike"] - strike))
    T = (dt.date.fromisoformat(expiry) - dt.date.fromisoformat(val_date)).days / 365.0
    curve, _ = treasury_curve(day)
    rate = cc_rate(interp(curve, T))
    iv = bs.implied_vol(r_["mid"], close, r_["strike"], T, rate)
    return {"iv": iv, "strike": r_["strike"], "expiry": expiry, "mid": r_["mid"], "cboe_iv": r_["cboe_iv"],
            "spot": close, "T": T, "source": src}
