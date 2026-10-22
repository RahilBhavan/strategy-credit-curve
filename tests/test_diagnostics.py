"""Authored fixtures exercise diagnostics, never certify market observations."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from credit_curve import diagnostics, inputs, notes, run


class MarketDiagnostics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.market_path = self.root / 'market.json'
        self.mark_path = self.root / 'marks.json'
        self.out = self.root / 'report.json'
        self.data = json.loads(inputs.DEFAULT.read_text())
        self.data['kind'] = 'user_supplied'
        source = {'description': 'Authored test fixture; not an observed market quote',
                  'as_of': '2026-10-21', 'fetched_utc': '2026-10-22T00:30:00Z', 'url': None}
        for quote in self.data['quotes'].values():
            quote['source'] = copy.deepcopy(source)
        self.data['strk_option_volatility']['source'] = copy.deepcopy(source)
        self.marks = {'schema_version': 1, 'kind': 'user_supplied', 'valuation_date': '2026-10-21',
                      'marks': {name: {'price': 1000, 'currency': 'USD', 'face_amount': 1000,
                                      'price_basis': 'dirty', 'price_date': '2026-10-21',
                                      'quote_type': 'indicative', 'source': copy.deepcopy(source)}
                                for name in notes.NAMES}}

    def files(self):
        self.market_path.write_text(json.dumps(self.data))
        self.mark_path.write_text(json.dumps(self.marks))
        return inputs.load(self.market_path), diagnostics.load_marks(self.mark_path, '2026-10-21')

    def cli(self, *extra):
        self.market_path.write_text(json.dumps(self.data))
        self.mark_path.write_text(json.dumps(self.marks))
        with patch('sys.argv', ['diagnostics', '--market-input', str(self.market_path),
                                '--note-marks', str(self.mark_path), '--out', str(self.out),
                                '--steps', '80', *extra]), \
                patch('urllib.request.urlopen', side_effect=AssertionError('offline required')), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            diagnostics.main()

    def test_default_synthetic_is_diagnostic_only(self):
        report = diagnostics.build(inputs.load())
        self.assertFalse(report['all_inputs_ready'])
        self.assertEqual(report['coverage']['STRE']['reasons'],
                         ['synthetic_assumption', 'missing_observation_date', 'missing_retrieval_timestamp'])
        for row in report['notes']:
            self.assertIsNone(row['comparisons'])
            self.assertIn('missing_note_mark', row['reasons'])
            self.assertIsNone(row['supplied_mark'])

    def test_all_scenarios_preserve_values_and_difference_sign_units(self):
        data, marks = self.files()
        report = diagnostics.build(data, marks, steps=80)
        original = run.note_scenarios(80, data)
        self.assertTrue(report['all_inputs_ready'])
        self.assertEqual(report['market_inputs']['input_sha256'], hashlib.sha256(self.market_path.read_bytes()).hexdigest())
        self.assertEqual(report['note_marks_sha256'], hashlib.sha256(self.mark_path.read_bytes()).hexdigest())
        for row, model in zip(report['notes'], original['notes']):
            self.assertEqual(len(row['comparisons']), 9)
            self.assertFalse(row['quality']['independently_verified'])
            for comparison, value in zip(row['comparisons'], model['scenarios']):
                for key in value:
                    self.assertEqual(comparison[key], value[key])
                self.assertEqual(comparison['model_minus_supplied_usd'], value['value_per_1000_usd'] - 1000)
                self.assertAlmostEqual(comparison['model_minus_supplied_pct'], (value['value_per_1000_usd'] - 1000) / 10)

    def test_missing_and_stale_marks_do_not_substitute_filing_values(self):
        self.marks['marks'].pop('2028')
        self.marks['marks']['2029']['source']['as_of'] = '2026-06-30'
        report = diagnostics.build(*self.files(), steps=80)
        first, second, third = report['notes'][:3]
        self.assertEqual(first['reasons'], ['missing_note_mark'])
        self.assertIsNone(first['comparisons'])
        self.assertIsNone(second['comparisons'])
        self.assertEqual(second['quality']['age_calendar_days'], 113)
        self.assertIn('stale_observation', second['reasons'])
        self.assertIsNotNone(third['comparisons'])

    def test_missing_stale_or_undated_mstr_blocks_every_note(self):
        for change, reason in (({'as_of': '2026-10-20'}, 'stale_observation'),
                               ({'as_of': None}, 'missing_observation_date'),
                               ({'fetched_utc': None}, 'missing_retrieval_timestamp')):
            with self.subTest(change=change):
                self.data['quotes']['MSTR']['source'].update(change)
                with patch.object(run, 'note_scenarios', side_effect=AssertionError('must refuse before pricing')):
                    report = diagnostics.build(*self.files())
                for row in report['notes']:
                    self.assertIn('MSTR:' + reason, row['reasons'])
                    self.assertIsNone(row['comparisons'])

    def test_stale_stre_is_visible_without_blocking_independent_notes(self):
        self.data['quotes']['STRE']['source']['as_of'] = '2025-11-06'
        report = diagnostics.build(*self.files(), steps=80)
        self.assertFalse(report['all_inputs_ready'])
        self.assertEqual(report['coverage']['STRE']['age_calendar_days'], 349)
        self.assertTrue(all(r['comparisons'] for r in report['notes']))

    def test_bad_basis_units_prices_and_dates_fail_before_output(self):
        bad = [('price_basis', 'clean'), ('currency', 'EUR'), ('face_amount', 100),
               ('price', True), ('price', -1), ('quote_type', 'close'), ('price_date', '2026-10-22')]
        for field, value in bad:
            with self.subTest(field=field):
                self.marks['marks']['2028'][field] = value
                with self.assertRaises(SystemExit) as error:
                    self.cli()
                self.assertEqual(error.exception.code, 2)
                self.assertFalse(self.out.exists())
                self.marks['marks']['2028'][field] = {'price_basis': 'dirty', 'currency': 'USD',
                    'face_amount': 1000, 'price': 1000, 'quote_type': 'indicative', 'price_date': '2026-10-21'}[field]

    def test_both_boundaries_reject_duplicate_keys_and_nonfinite_constants(self):
        for raw in ('{"schema_version":1,"schema_version":1}', '{"price":NaN}'):
            self.market_path.write_text(raw)
            for loader in (inputs.load, lambda p: diagnostics.load_marks(p, '2026-10-21')):
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    loader(self.market_path)

    def test_source_date_order_canonical_dates_and_utc_are_validated(self):
        for change in ({'as_of': '20261021'}, {'as_of': '2026-02-30'},
                       {'as_of': '2026-10-22'}, {'fetched_utc': '2026-10-20T23:59:00Z'},
                       {'fetched_utc': '2026-10-21T12:00:00'}, {'fetched_utc': '2026-10-21T12:00:00+01:00'}):
            for target in ('market', 'mark'):
                with self.subTest(change=change, target=target):
                    source = (self.data['quotes']['MSTR'] if target == 'market' else self.marks['marks']['2028'])['source']
                    original = copy.deepcopy(source)
                    source.update(change)
                    with self.assertRaises(ValueError):
                        self.files()
                    source.clear()
                    source.update(original)

    def test_cli_is_offline_repeatable_and_strict_failure_retains_report(self):
        self.cli('--require-complete')
        first = self.out.read_bytes()
        self.cli('--require-complete')
        self.assertEqual(first, self.out.read_bytes())
        self.marks['marks'].pop('2032')
        with self.assertRaises(SystemExit) as error:
            self.cli('--require-complete')
        self.assertEqual(error.exception.code, 3)
        self.assertFalse(json.loads(self.out.read_text())['all_inputs_ready'])

    def test_output_cannot_overwrite_source(self):
        self.files()
        body = self.market_path.read_bytes()
        self.out = self.market_path
        with self.assertRaises(SystemExit) as error:
            self.cli()
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(self.market_path.read_bytes(), body)
