"""Freeze exchange daily closes for MSTR and the preferreds into a schema-v1 market-input file.

Run: python scripts/fetch_closes.py 2026-10-21

Primary source: Nasdaq's historical-quote API, the listing exchange for MSTR, STRF, STRC, STRK and STRD.
Cross-check: Yahoo Finance daily chart bars, which must round to the same close. STRE lists only on the
Luxembourg Stock Exchange; it gets a price only if Yahoo's STRE.LU bar for the date shows traded volume.

Response bodies stay in ignored data/local/closes/<date>/; the committed file keeps each URL, retrieval
time, byte count and SHA-256, plus the extracted close and volume.
"""
import datetime as dt
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NASDAQ = ('MSTR', 'STRF', 'STRC', 'STRK', 'STRD')
UA = 'Mozilla/5.0 (X11; Linux x86_64) RahilBhavan-research'
VOLATILITY_NOTE = ('Authored assumption, not an observed or implied volatility. It feeds the finite-horizon '
                   'STRK conversion-call scenarios only.')


def get(url, cache):
    request = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=40) as response:
        body = response.read()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return json.loads(body), {'url': url, 'fetched_utc': stamp, 'bytes': len(body),
                              'sha256': hashlib.sha256(body).hexdigest()}


def yahoo_bars(symbol, day, cache_dir):
    start = int(dt.datetime(int(day[:4]), 1, 1, tzinfo=dt.timezone.utc).timestamp())
    end = int((dt.datetime.fromisoformat(day) + dt.timedelta(days=1)).replace(tzinfo=dt.timezone.utc).timestamp())
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start}&period2={end}&interval=1d'
    body, meta = get(url, cache_dir / f'yahoo-{symbol}.json')
    result = body['chart']['result'][0]
    quote = result['indicators']['quote'][0]
    bars = {dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat(): (c, v)
            for t, c, v in zip(result['timestamp'], quote['close'], quote['volume']) if c is not None}
    return bars, result['meta']['currency'], meta


def nasdaq_close(ticker, day, cache_dir):
    start = (dt.date.fromisoformat(day) - dt.timedelta(days=7)).isoformat()  # API rejects fromdate == todate
    url = (f'https://api.nasdaq.com/api/quote/{ticker}/historical?assetclass=stocks'
           f'&fromdate={start}&todate={day}&limit=10')
    body, meta = get(url, cache_dir / f'nasdaq-{ticker}.json')
    us_day = dt.date.fromisoformat(day).strftime('%m/%d/%Y')
    row = next(r for r in body['data']['tradesTable']['rows'] if r['date'] == us_day)
    return float(row['close'].lstrip('$').replace(',', '')), int(row['volume'].replace(',', '')), meta


def quotes(day, cache_dir):
    out = {}
    for ticker in NASDAQ:
        close, volume, meta = nasdaq_close(ticker, day, cache_dir)
        bars, currency, cross = yahoo_bars(ticker, day, cache_dir)
        if currency != 'USD' or round(bars[day][0], 2) != close:
            raise SystemExit(f'{ticker}: Nasdaq close {close} disagrees with Yahoo {bars.get(day)} {currency}')
        out[ticker] = {'price': close, 'currency': 'USD', 'source': {
            'description': f'Nasdaq historical daily close, {day}; volume {volume:,} shares. '
                           'Yahoo Finance daily bar agrees to the cent.',
            'as_of': day, **meta, 'volume': volume,
            'cross_check': {'close': round(bars[day][0], 4), **cross}}}
    bars, currency, meta = yahoo_bars('STRE.LU', day, cache_dir)
    traded = [d for d, (_, volume) in sorted(bars.items()) if volume]
    if currency != 'EUR':
        raise SystemExit(f'STRE.LU currency {currency}, expected EUR')
    if traded and traded[-1] == day:
        out['STRE'] = {'price': round(bars[day][0], 4), 'currency': 'EUR', 'source': {
            'description': f'Luxembourg Stock Exchange close via Yahoo Finance STRE.LU, {day}.',
            'as_of': day, **meta, 'volume': bars[day][1]}}
    else:
        last = traded[-1] if traded else None
        note = 'no STRE.LU bar with traded volume in the fetched year' if last is None else (
            f'last STRE.LU bar with traded volume was {last} at EUR {bars[last][0]:.2f} '
            f'({bars[last][1]:,} shares); every later bar repeats that price on zero volume')
        out['STRE'] = {'price': None, 'currency': 'EUR', 'unavailable': f'No {day} trade: {note}.',
                       'source': {'description': 'Yahoo Finance STRE.LU daily bars (Luxembourg Stock Exchange).',
                                  'as_of': last, **meta}}
    return out


def main(day):
    cache_dir = ROOT / 'data/local/closes' / day
    data = {'schema_version': 1, 'kind': 'exchange_close', 'valuation_date': day, 'quotes': quotes(day, cache_dir),
            'strk_option_volatility': {'base': 0.6, 'sensitivity': 0.8, 'source': {
                'description': VOLATILITY_NOTE, 'as_of': None, 'fetched_utc': None, 'url': None}}}
    target = ROOT / 'data/market' / day / 'closes.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    print(f'{target.relative_to(ROOT)}: ' + ', '.join(
        f'{t} {q["price"]}' for t, q in data['quotes'].items()))


if __name__ == '__main__':
    main(sys.argv[1])
