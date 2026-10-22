"""Fetch and cache market inputs for one snapshot date (free public sources).

Run: python -m credit_curve.market_fetch 2026-10-21
"""
import sys
from . import fetch

TICKERS = ["STRF", "STRC", "STRK", "STRD", "MSTR"]


def urls(day):
    y = day[:4]
    u = {}
    for t in TICKERS:
        u[f"market/{day}/nasdaq-{t}.json"] = f"https://api.nasdaq.com/api/quote/{t}/info?assetclass=stocks"
        u[f"market/{day}/yahoo-{t}-1y.json"] = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=1y&interval=1d"
    u[f"market/{day}/treasury-par-{y}.csv"] = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                                              f"daily-treasury-rates.csv/{y}/all?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv")
    u[f"market/{day}/sofr-last10.json"] = "https://markets.newyorkfed.org/api/rates/secured/sofr/last/10.json"
    for m in ("1Y", "3Y", "5Y", "10Y", "20Y", "30Y"):
        u[f"market/{day}/ecb-aaa-spot-{m}.csv"] = (f"https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_{m}"
                                                   "?lastNObservations=5&format=csvdata")
    u[f"market/{day}/ecb-estr.csv"] = "https://data-api.ecb.europa.eu/service/data/EST/B.EU000A2X2A25.WT?lastNObservations=5&format=csvdata"
    u[f"market/{day}/ecb-eurusd.csv"] = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?lastNObservations=5&format=csvdata"
    u[f"market/{day}/cboe-MSTR-options.json"] = "https://cdn.cboe.com/api/global/delayed_quotes/options/MSTR.json"
    return u


def main(day):
    failed = False
    for rel, url in urls(day).items():
        try:
            fetch.get(url, rel)
            print("ok", rel)
        except RuntimeError as e:
            failed = True
            print("FAIL", rel, e)
    return int(failed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
