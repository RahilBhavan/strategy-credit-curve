"""Parse portable market assumptions at the file boundary; never fetch or infer quotes."""
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'data/scenarios/market-inputs.json'
CURRENCIES = {'MSTR': 'USD', 'STRF': 'USD', 'STRC': 'USD', 'STRE': 'EUR', 'STRK': 'USD', 'STRD': 'USD'}


def load(path=DEFAULT):
    """Validate schema v1. User files must supply their own source/as-of descriptions."""
    data, digest = read_json(path)
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
        raise ValueError('market inputs require schema_version 1')
    if data.get('kind') not in ('synthetic_scenario', 'user_supplied'):
        raise ValueError('kind must be synthetic_scenario or user_supplied')
    if data.get('valuation_date') != '2026-10-21':
        raise ValueError('this frozen contract/rate comparison supports valuation_date 2026-10-21 only')
    quotes = data.get('quotes')
    if not isinstance(quotes, dict) or set(quotes) != set(CURRENCIES):
        raise ValueError('quotes must contain exactly MSTR, STRF, STRC, STRE, STRK and STRD')
    for ticker, currency in CURRENCIES.items():
        quote = quotes[ticker]
        if not isinstance(quote, dict) or quote.get('currency') != currency:
            raise ValueError(f'{ticker} must be a {currency} quote')
        validate_positive(quote.get('price'), f'{ticker} price')
        validate_source(quote.get('source'), ticker)
        if quote['source']['as_of'] is not None and quote['source']['as_of'] > data['valuation_date']:
            raise ValueError(f'{ticker} observation is after the frozen valuation date')
        if data['kind'] == 'synthetic_scenario' and quote['source']['as_of'] is not None:
            raise ValueError('synthetic prices have no market observation date; use as_of null')
    vols = data.get('strk_option_volatility')
    if not isinstance(vols, dict) or set(vols) != {'base', 'sensitivity', 'source'}:
        raise ValueError('strk_option_volatility requires base, sensitivity and source')
    for key in ('base', 'sensitivity'):
        validate_positive(vols[key], f'{key} option volatility')
    validate_source(vols['source'], 'option volatility')
    if vols['source']['as_of'] is not None and vols['source']['as_of'] > data['valuation_date']:
        raise ValueError('option volatility observation is after the frozen valuation date')
    if data['kind'] == 'synthetic_scenario' and vols['source']['as_of'] is not None:
        raise ValueError('synthetic volatility has no observation date; use as_of null')
    data['input_sha256'] = digest
    return data


def validate_positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and positive')


def validate_source(source, name):
    if not isinstance(source, dict) or not isinstance(source.get('description'), str) or not source['description'].strip():
        raise ValueError(f'{name} requires a source description')
    for key in ('as_of', 'fetched_utc'):
        if key not in source:
            raise ValueError(f'{name} source requires {key} (null when unavailable)')
        if source[key] is not None and not isinstance(source[key], str):
            raise ValueError(f'{name} source {key} must be a string or null')
    if source['as_of'] is not None:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', source['as_of']):
            raise ValueError(f'{name} as_of must be YYYY-MM-DD')
        dt.date.fromisoformat(source['as_of'])
    if source['fetched_utc'] is not None:
        stamp = dt.datetime.fromisoformat(source['fetched_utc'].replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset() != dt.timedelta(0):
            raise ValueError('fetched_utc must carry the UTC timezone')
        if 'T' not in source['fetched_utc']:
            raise ValueError('fetched_utc must be an ISO datetime with T separator')
        if source['as_of'] is not None and stamp.date().isoformat() < source['as_of']:
            raise ValueError(f'{name} retrieval precedes observation date')
    if source.get('url') is not None:
        if not isinstance(source['url'], str) or not source['url'].startswith('https://'):
            raise ValueError('source URL must be an HTTPS string or null')


def quote(data, ticker):
    row = data['quotes'][ticker]
    return {'price': row['price'], 'currency': row['currency'],
            'source': {**row['source'], 'kind': data['kind']}}


def provenance(data):
    return {'schema_version': data['schema_version'], 'kind': data['kind'],
            'valuation_date': data['valuation_date'], 'input_sha256': data['input_sha256'],
            'interpretation': 'Synthetic prices/volatilities are authored assumptions, not market observations. '
                              'User-supplied observations remain the responsibility of their supplier.'}


def read_json(path):
    """Read auditable JSON without silent last-key-wins or nonstandard constants."""
    raw = Path(path).read_bytes()

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'duplicate JSON key: {key}')
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f'nonfinite JSON constant: {value}')

    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid), hashlib.sha256(raw).hexdigest()
