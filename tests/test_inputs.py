"""Portable input validation and observable scenario changes, with no provider data."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from credit_curve import curve, inputs, run


class PortableInputs(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(inputs.DEFAULT.read_text())
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'inputs.json'

    def load(self, data):
        self.path.write_text(json.dumps(data))
        return inputs.load(self.path)

    def test_synthetic_prices_are_never_mislabeled_as_observations(self):
        data = self.load(self.fixture)
        self.assertEqual(data['kind'], 'synthetic_scenario')
        self.assertEqual(len(data['input_sha256']), 64)
        for row in curve.build(data)['rows']:
            self.assertTrue(row['price_is_synthetic'])
            self.assertIsNone(row['price_source']['as_of'])
            self.assertIsNone(row['price_source']['fetched_utc'])
            self.assertFalse(row['live_ranking_eligible'])

    def test_rejects_malformed_or_misdated_inputs(self):
        changes = [lambda d: d.update(schema_version=2),
                   lambda d: d.update(kind='observed_live'),
                   lambda d: d['quotes'].pop('STRE'),
                   lambda d: d['quotes']['STRE'].update(currency='USD'),
                   lambda d: d['quotes']['MSTR'].update(price=True),
                   lambda d: d['quotes']['MSTR'].update(price=float('nan')),
                   lambda d: d['quotes']['MSTR'].update(price=-1),
                   lambda d: d['strk_option_volatility'].update(base=0),
                   lambda d: d['quotes']['STRE']['source'].update(as_of='2026-10-21'),
                   lambda d: d['quotes']['STRE']['source'].update(description=''),
                   lambda d: d.update(valuation_date='2027-01-01')]
        for change in changes:
            data = copy.deepcopy(self.fixture)
            change(data)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.load(data)

    def test_user_supplied_dates_and_sources_remain_separate(self):
        self.fixture['kind'] = 'user_supplied'
        self.fixture['quotes']['STRE']['source'] = {
            'description': 'User-authored testing observation, not a real trade',
            'as_of': '2025-11-06', 'fetched_utc': '2026-10-22T01:00:00Z', 'url': None}
        data = self.load(self.fixture)
        stre = next(r for r in curve.build(data)['rows'] if r['ticker'] == 'STRE')
        self.assertTrue(stre['price_is_stale'])
        self.assertFalse(stre['price_is_synthetic'])
        self.assertEqual(stre['price_source']['as_of'], '2025-11-06')
        self.assertEqual(stre['price_source']['fetched_utc'], '2026-10-22T01:00:00Z')
        self.fixture['quotes']['STRE']['source']['as_of'] = '2026-10-22'
        with self.assertRaisesRegex(ValueError, 'after valuation_date 2026-10-21.*--rates'):
            self.load(self.fixture)

    def test_cli_uses_user_file_to_change_all_six_note_values(self):
        self.fixture['kind'] = 'user_supplied'
        self.fixture['quotes']['MSTR']['price'] = 300
        self.load(self.fixture)
        out = Path(self.tmp.name) / 'out'
        with patch('sys.argv', ['credit_curve.run', '--market-input', str(self.path), '--out', str(out)]), \
             patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')), \
             contextlib.redirect_stdout(io.StringIO()):
            run.main()
        result = json.loads((out / 'convertibles.json').read_text())
        base = json.loads((run.ROOT / 'results/convertibles.json').read_text())
        self.assertEqual(result['spot'], 300)
        self.assertEqual(result['market_inputs']['kind'], 'user_supplied')
        for changed, original in zip(result['notes'], base['notes']):
            self.assertGreater(changed['scenarios'][4]['value_per_1000_usd'], original['scenarios'][4]['value_per_1000_usd'])

    def test_cli_rejects_bad_input_before_writing(self):
        self.fixture['quotes']['STRC']['price'] = 0
        self.path.write_text(json.dumps(self.fixture))
        out = Path(self.tmp.name) / 'absent'
        with patch('sys.argv', ['credit_curve.run', '--market-input', str(self.path), '--out', str(out)]), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            run.main()
        self.assertEqual(error.exception.code, 2)
        self.assertFalse(out.exists())

    def test_extreme_strc_prices_have_valid_call_yields(self):
        for price in (25, 250):
            with self.subTest(price=price):
                self.fixture['quotes']['STRC']['price'] = price
                row = next(r for r in curve.build(self.load(self.fixture))['rows'] if r['ticker'] == 'STRC')
                y = row['ytc_1y_at_101']
                pv = sum((12 / 24) / (1 + y)**(k / 24) for k in range(1, 25)) + 101 / (1 + y)
                self.assertAlmostEqual(pv, price, delta=1e-8)

    def test_malformed_provenance_exits_two_without_output(self):
        for field in ('url', 'fetched_utc'):
            with self.subTest(field=field):
                data = copy.deepcopy(self.fixture)
                data['quotes']['MSTR']['source'][field] = 123
                self.path.write_text(json.dumps(data))
                out = Path(self.tmp.name) / 'absent'
                with patch('sys.argv', ['credit_curve.run', '--market-input', str(self.path), '--out', str(out)]), \
                     contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    run.main()
                self.assertEqual(error.exception.code, 2)
                self.assertFalse(out.exists())

    def test_impossible_option_adjustment_is_explicit(self):
        self.fixture['quotes']['STRK']['price'] = 1
        with self.assertRaisesRegex(ValueError, 'nonpositive straight-price'):
            curve.build(self.load(self.fixture))
