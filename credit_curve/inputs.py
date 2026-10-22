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


TERMS_SNAPSHOT = '2026-10-21'
NOTE_NAMES = ('2028', '2029', '2030A', '2030B', '2031', '2032')


def load(path=DEFAULT, rates_path=None):
    """Validate schema v1 and attach the benchmark-rate snapshot for its valuation date.

    Without ``rates_path`` only the bundled 2026-10-21 rates exist, so other dates need a rates file."""
    from . import rates as benchmark_rates  # rates validates sources with this module's helpers

    data, digest = read_json(path)
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
        raise ValueError('market inputs require schema_version 1')
    if data.get('kind') not in ('synthetic_scenario', 'user_supplied'):
        raise ValueError('kind must be synthetic_scenario or user_supplied')
    day = valuation_date(data.get('valuation_date'), 'market inputs')
    quotes = data.get('quotes')
    if not isinstance(quotes, dict) or set(quotes) != set(CURRENCIES):
        raise ValueError('quotes must contain exactly MSTR, STRF, STRC, STRE, STRK and STRD')
    for ticker, currency in CURRENCIES.items():
        quote = quotes[ticker]
        if not isinstance(quote, dict) or quote.get('currency') != currency:
            raise ValueError(f'{ticker} must be a {currency} quote')
        validate_positive(quote.get('price'), f'{ticker} price')
        observed_by(quote.get('source'), ticker, data['kind'], day)
    vols = data.get('strk_option_volatility')
    if not isinstance(vols, dict) or set(vols) != {'base', 'sensitivity', 'source'}:
        raise ValueError('strk_option_volatility requires base, sensitivity and source')
    for key in ('base', 'sensitivity'):
        validate_positive(vols[key], f'{key} option volatility')
    observed_by(vols['source'], 'option volatility', data['kind'], day)
    data['note_assumptions'] = note_assumptions(data.get('note_assumptions'), data['kind'], day)
    if rates_path is not None:
        rates = benchmark_rates.load(rates_path)
        if rates['valuation_date'] != day:
            raise ValueError(f'rates file valuation_date {rates["valuation_date"]} must equal market inputs '
                             f'valuation_date {day}')
    elif day != benchmark_rates.FROZEN_DATE:
        raise ValueError(f'valuation_date {day} needs benchmark rates for that date: pass --rates FILE '
                         f'(schema in docs/market-inputs.md). The bundled snapshot covers '
                         f'{benchmark_rates.FROZEN_DATE} only.')
    else:
        rates = benchmark_rates.frozen()
    data['input_sha256'] = digest
    data['rates'] = rates
    return data


def valuation_date(value, name):
    """ISO date on or after the contract-terms snapshot; earlier terms are not reconstructed."""
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError(f'{name} valuation_date must be YYYY-MM-DD')
    dt.date.fromisoformat(value)
    if value < TERMS_SNAPSHOT:
        raise ValueError(f'{name} valuation_date {value} precedes the {TERMS_SNAPSHOT} contract-terms snapshot; '
                         'historical terms are not reconstructed')
    return value


def observed_by(source, name, kind, day):
    validate_source(source, name)
    if source['as_of'] is not None and source['as_of'] > day:
        raise ValueError(f'{name} observation {source["as_of"]} is after valuation_date {day}; '
                         'set valuation_date to that date and pass --rates for it')
    if kind == 'synthetic_scenario' and source['as_of'] is not None:
        raise ValueError(f'synthetic {name} has no market observation date; use as_of null')


def note_assumptions(value, kind, day):
    """Optional per-note implied volatility and credit spread; the default grid always runs too."""
    if value is None:
        return {}
    if not isinstance(value, dict) or not set(value) <= set(NOTE_NAMES):
        raise ValueError(f'note_assumptions keys must be a subset of {", ".join(NOTE_NAMES)}')
    for name, item in value.items():
        if not isinstance(item, dict) or set(item) != {'volatility', 'credit_spread', 'source'}:
            raise ValueError(f'note_assumptions {name} requires volatility, credit_spread and source')
        vol, spread = item['volatility'], item['credit_spread']
        for label, number, lo, hi in (('volatility', vol, 0.01, 5.0), ('credit_spread', spread, 0.0, 0.5)):
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) \
                    or not lo <= number <= hi:
                raise ValueError(f'note_assumptions {name} {label} must be a decimal in [{lo}, {hi}] '
                                 '(60% volatility is 0.6; 500 bp spread is 0.05)')
        observed_by(item['source'], f'{name} note assumption', kind, day)
    return value


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
    from . import rates as benchmark_rates

    return {'schema_version': data['schema_version'], 'kind': data['kind'],
            'valuation_date': data['valuation_date'], 'input_sha256': data['input_sha256'],
            'rates': benchmark_rates.provenance(data['rates']),
            'contract_terms_snapshot': TERMS_SNAPSHOT,
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
