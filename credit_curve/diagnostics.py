"""Offline freshness diagnostics and conditional note-mark comparisons.

Run with python -m credit_curve.diagnostics. No source is certified as live.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

from . import inputs, notes, run


def load_marks(path, valuation_date):
    """Validate a separate local schema; never migrate the pinned market schema."""
    data, digest = inputs.read_json(path)
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
        raise ValueError('note marks require schema_version 1')
    if data.get('kind') != 'user_supplied' or data.get('valuation_date') != valuation_date:
        raise ValueError(f'note marks require kind user_supplied and valuation_date {valuation_date} '
                         '(the market-input valuation date)')
    marks = data.get('marks')
    if not isinstance(marks, dict) or not set(marks) <= set(notes.NAMES):
        raise ValueError('marks must be a subset of supported note names')
    for name, mark in marks.items():
        if not isinstance(mark, dict) or mark.get('currency') != 'USD' or mark.get('face_amount') != 1000:
            raise ValueError(f'{name} mark must be USD per 1000 face_amount')
        if mark.get('price_basis') != 'dirty' or mark.get('price_date') != valuation_date:
            raise ValueError(f'{name} requires dirty price_basis and price_date equal to valuation_date')
        if mark.get('quote_type') not in ('bid', 'ask', 'mid', 'trade', 'indicative'):
            raise ValueError(f'{name} requires quote_type bid, ask, mid, trade or indicative')
        inputs.validate_positive(mark.get('price'), f'{name} price')
        inputs.validate_source(mark.get('source'), name)
        if mark['source']['as_of'] is not None and mark['source']['as_of'] > valuation_date:
            raise ValueError(f'{name} observation {mark["source"]["as_of"]} is after valuation_date {valuation_date}; '
                             'set both files to that date and pass --rates for it')
    return {'input_sha256': digest, 'marks': marks, 'kind': data['kind']}


def assess(source, kind, valuation_date):
    """Calendar-day policy relative to the valuation date, independent of today's clock."""
    observed = source['as_of']
    age = None if observed is None else (dt.date.fromisoformat(valuation_date) - dt.date.fromisoformat(observed)).days
    reasons = []
    if kind == 'synthetic_scenario':
        reasons.append('synthetic_assumption')
    if observed is None:
        reasons.append('missing_observation_date')
    elif age > 0:
        reasons.append('stale_observation')
    if source['fetched_utc'] is None:
        reasons.append('missing_retrieval_timestamp')
    return {'source': source, 'kind': kind, 'age_calendar_days': age,
            'usable_for_snapshot_comparison': not reasons, 'reasons': reasons,
            'independently_verified': False}


def build(data, marks=None, steps=600):
    day, kind = data['valuation_date'], data['kind']
    coverage = {ticker: {**assess(q['source'], kind, day), 'price': q['price'], 'currency': q['currency']}
                for ticker, q in data['quotes'].items()}
    for item in coverage.values():
        if item['price'] is None:
            item['reasons'].append('no_observed_price')
            item['usable_for_snapshot_comparison'] = False
    coverage['strk_option_volatility'] = assess(data['strk_option_volatility']['source'], kind, day)
    note_rows = []
    supplied = {} if marks is None else marks['marks']
    # Reuse the unchanged model, but only run it when a comparison can be made.
    comparable = {name for name, mark in supplied.items()
                  if assess(mark['source'], 'user_supplied', day)['usable_for_snapshot_comparison']
                  and coverage['MSTR']['usable_for_snapshot_comparison']}
    model = run.note_scenarios(steps, data) if comparable else None
    model_rows = {} if model is None else {r['terms']['name']: r for r in model['notes']}
    for name in notes.NAMES:
        mark = supplied.get(name)
        quality = None if mark is None else assess(mark['source'], 'user_supplied', day)
        reasons = ['missing_note_mark'] if quality is None else list(quality['reasons'])
        reasons += ['MSTR:' + reason for reason in coverage['MSTR']['reasons']]
        comparisons = None
        if name in comparable:
            comparisons = []
            for scenario in model_rows[name]['scenarios']:
                difference = scenario['value_per_1000_usd'] - mark['price']
                comparisons.append({**scenario, 'model_minus_supplied_usd': difference,
                                    'model_minus_supplied_pct': 100 * difference / mark['price']})
        note_rows.append({'name': name, 'supplied_mark': mark, 'quality': quality,
                          'reasons': reasons, 'comparisons': comparisons})
    return {'schema_version': 1, 'valuation_date': day, 'market_inputs': inputs.provenance(data),
            'note_marks_sha256': None if marks is None else marks['input_sha256'],
            'policy': 'Same valuation-date observation and retrieval timestamp required; calendar days, no grace period. '
                      'Same-day dates do not establish synchronized intraday observations.',
            'all_inputs_ready': all(c['usable_for_snapshot_comparison'] for c in coverage.values())
                                and all(r['comparisons'] is not None for r in note_rows),
            'coverage': coverage, 'steps': steps, 'notes': note_rows,
            'interpretation': 'User-supplied marks are unverified, never live-certified. Differences are conditional '
                              'on assumed volatility/spread, not fitted spreads, mispricing or trading signals. '
                              'Model values and supplied dirty prices are USD per $1,000 face at valuation, excluding '
                              'fees. Exact accrual, settlement and record-date ownership remain model limitations. '
                              'Preferred input diagnostics are not preferred model valuations.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market-input', type=Path, default=inputs.DEFAULT)
    parser.add_argument('--rates', type=Path, help='schema-v1 benchmark rates for a valuation date other than 2026-10-21')
    parser.add_argument('--note-marks', type=Path, help='local user-supplied schema-v1 note marks')
    parser.add_argument('--out', type=Path, required=True, help='diagnostic JSON path')
    parser.add_argument('--steps', type=int, default=600)
    parser.add_argument('--require-complete', action='store_true', help='exit 3 after report if any input/mark is unusable')
    args = parser.parse_args()
    if not 2 <= args.steps <= 10000:
        parser.error('steps must lie in [2,10000]')
    # A report must never overwrite either of its evidence files (including symlinks).
    if args.out.resolve() in {p.resolve() for p in (args.market_input, args.rates, args.note_marks) if p is not None}:
        parser.error('output must differ from input files')
    try:
        data = inputs.load(args.market_input, args.rates)
        marks = None if args.note_marks is None else load_marks(args.note_marks, data['valuation_date'])
        report = build(data, marks, args.steps)
        body = json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n'
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(body)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    print(f'Wrote diagnostics to {args.out}; all_inputs_ready={report["all_inputs_ready"]}')
    if args.require_complete and not report['all_inputs_ready']:
        raise SystemExit(3)


if __name__ == '__main__':
    main()
