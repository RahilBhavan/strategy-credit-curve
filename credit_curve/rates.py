"""Benchmark-rate snapshots: the bundled 2026-10-21 public snapshot or a validated user file.

Every snapshot has one shape so the preferred comparison and note pricer never care where the
rates came from:

    {"kind", "valuation_date", "input_sha256",
     "ust_par_yield": {"tenors": {years: decimal BEY}, "source"},
     "sofr" | "ecb_aaa_spot_30y" | "eurusd": {"rate", "source"}}
"""
import math

from . import inputs, market

FROZEN_DATE = market.SNAP
KINDS = ('synthetic_scenario', 'user_supplied')
SERIES = {  # name -> (lower, upper, unit) sanity bounds that catch percent-vs-decimal mistakes
    'sofr': (-0.05, 0.5, 'decimal rate'),
    'ecb_aaa_spot_30y': (-0.05, 0.5, 'decimal continuously compounded rate'),
    'eurusd': (0.2, 5.0, 'USD per EUR'),
}
KEYS = {'schema_version', 'kind', 'valuation_date', 'ust_par_yield', *SERIES}


def frozen():
    """The public snapshot restored from data/raw/market/2026-10-21 (attributed, hashed sources)."""
    curve, csrc = market.treasury_curve()
    sofr, ssrc = market.sofr()
    eur30, esrc = market.ecb_aaa_spot('30Y')
    fx, fxsrc = market.eurusd()
    return {'kind': 'frozen_public_snapshot', 'valuation_date': FROZEN_DATE, 'input_sha256': None,
            'ust_par_yield': {'tenors': curve, 'source': csrc},
            'sofr': {'rate': sofr, 'source': ssrc},
            'ecb_aaa_spot_30y': {'rate': eur30, 'source': esrc},
            'eurusd': {'rate': fx, 'source': fxsrc}}


def load(path):
    """Validate a schema-v1 rates file. Errors name the field and the expected unit."""
    data, digest = inputs.read_json(path)
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
        raise ValueError('rates file requires schema_version 1')
    unknown = set(data) - KEYS
    missing = KEYS - set(data)
    if unknown or missing:
        raise ValueError(f'rates file keys must be exactly {sorted(KEYS)}; '
                         f'missing {sorted(missing)}, unexpected {sorted(unknown)}')
    if data['kind'] not in KINDS:
        raise ValueError('rates kind must be synthetic_scenario or user_supplied')
    day = inputs.valuation_date(data.get('valuation_date'), 'rates file')
    ust = data['ust_par_yield']
    if not isinstance(ust, dict) or set(ust) != {'tenors', 'source'} or not isinstance(ust['tenors'], dict):
        raise ValueError('ust_par_yield requires tenors (years -> decimal par yield) and source')
    tenors = {}
    for key, value in ust['tenors'].items():
        try:
            years = float(key)
        except ValueError:
            raise ValueError(f'ust_par_yield tenor {key!r} must be a number of years, e.g. "0.25" or "30"') from None
        if not math.isfinite(years) or not 0 < years <= 50:
            raise ValueError(f'ust_par_yield tenor {key!r} must lie in (0, 50] years')
        tenors[years] = bounded(value, -0.05, 0.5, f'ust_par_yield {key}y', 'decimal bond-equivalent yield')
    if 30.0 not in tenors or min(tenors) > 1:
        raise ValueError('ust_par_yield needs the 30-year tenor (preferred benchmark) and one tenor of 1 year or less')
    checked_source(ust['source'], 'ust_par_yield', data['kind'], day)
    out = {'kind': data['kind'], 'valuation_date': day, 'input_sha256': digest,
           'ust_par_yield': {'tenors': tenors, 'source': ust['source']}}
    for name, (lo, hi, unit) in SERIES.items():
        item = data[name]
        if not isinstance(item, dict) or set(item) != {'rate', 'source'}:
            raise ValueError(f'{name} requires rate and source')
        bounded(item['rate'], lo, hi, name, unit)
        checked_source(item['source'], name, data['kind'], day)
        out[name] = item
    return out


def bounded(value, lo, hi, name, unit):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number ({unit})')
    if not lo <= value <= hi:
        raise ValueError(f'{name} = {value} is outside [{lo}, {hi}] for a {unit}; '
                         'rates are decimals, so 4.5% is 0.045')
    return float(value)


def checked_source(source, name, kind, day):
    inputs.validate_source(source, name)
    if source['as_of'] is not None and source['as_of'] > day:
        raise ValueError(f'{name} observation {source["as_of"]} is after valuation_date {day}')
    if kind == 'synthetic_scenario' and source['as_of'] is not None:
        raise ValueError(f'synthetic {name} has no market observation date; use as_of null')


def provenance(rates):
    return {'kind': rates['kind'], 'valuation_date': rates['valuation_date'],
            'input_sha256': rates['input_sha256']}
