"""User valuation dates, rates snapshots and per-note assumptions, observed through the CLI."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from credit_curve import diagnostics, inputs, notes, rates, run, summary
from credit_curve.convertible import price

LATER = inputs.ROOT / 'data/scenarios/later-date'


class ValuationDate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.market = json.loads((LATER / 'market-inputs.json').read_text())
        self.rates = json.loads((LATER / 'rates.json').read_text())

    def write(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data))
        return path

    def cli(self, *args):
        out = self.root / 'out'
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch('sys.argv', ['credit_curve.run', '--out', str(out), *args]), \
             patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                run.main()
            except SystemExit as error:
                return error.code, stderr.getvalue(), out
        return 0, stdout.getvalue(), out

    def test_later_date_uses_the_supplied_rates_and_records_them(self):
        code, text, out = self.cli('--market-input', str(LATER / 'market-inputs.json'),
                                   '--rates', str(LATER / 'rates.json'))
        self.assertEqual(code, 0, text)
        preferred = json.loads((out / 'preferred.json').read_text())
        notes_out = json.loads((out / 'convertibles.json').read_text())
        self.assertEqual(preferred['as_of'], '2026-10-22')
        self.assertEqual(notes_out['as_of'], '2026-10-22')
        provenance = preferred['market_inputs']['rates']
        self.assertEqual(provenance['kind'], 'synthetic_scenario')
        self.assertEqual(len(provenance['input_sha256']), 64)
        self.assertAlmostEqual(preferred['benchmarks']['ust30']['effective'], (1 + 0.054 / 2) ** 2 - 1, places=15)
        strf = preferred['rows'][0]
        self.assertAlmostEqual(strf['spread_bp'], 1e4 * (strf['effective_yield'] - ((1 + 0.054 / 2) ** 2 - 1)))
        self.assertIn('valuation date 2026-10-22', text)
        self.assertIn('$892.64 @ 55% vol, 400 bp', text)

    def test_reader_case_user_marks_dated_after_snapshot(self):
        source = {'description': 'Authored test fixture; not an observed quote', 'as_of': '2026-10-22',
                  'fetched_utc': '2026-10-22T21:00:00Z', 'url': None}
        self.market['kind'] = self.rates['kind'] = 'user_supplied'
        for item in [*self.market['quotes'].values(), self.market['strk_option_volatility'],
                     *self.market['note_assumptions'].values()]:
            item['source'] = copy.deepcopy(source)
        for name in ('ust_par_yield', 'sofr', 'ecb_aaa_spot_30y', 'eurusd'):
            self.rates[name]['source'] = copy.deepcopy(source)
        data = inputs.load(self.write('m.json', self.market), self.write('r.json', self.rates))
        marks = {'schema_version': 1, 'kind': 'user_supplied', 'valuation_date': '2026-10-22',
                 'marks': {'2028': {'price': 1500, 'currency': 'USD', 'face_amount': 1000, 'price_basis': 'dirty',
                                    'price_date': '2026-10-22', 'quote_type': 'mid', 'source': source}}}
        report = diagnostics.build(data, diagnostics.load_marks(self.write('k.json', marks), '2026-10-22'))
        self.assertTrue(report['coverage']['MSTR']['usable_for_snapshot_comparison'])
        self.assertEqual(len(report['notes'][0]['comparisons']), 9)

    def test_other_dates_without_rates_fail_with_a_named_fix_before_writing(self):
        code, text, out = self.cli('--market-input', str(LATER / 'market-inputs.json'))
        self.assertEqual(code, 2)
        self.assertIn('valuation_date 2026-10-22 needs benchmark rates', text)
        self.assertIn('--rates FILE', text)
        self.assertFalse(out.exists())

    def test_rates_file_is_validated_at_entry(self):
        market = self.write('m.json', self.market)
        cases = {
            'decimals': lambda r: r['sofr'].update(rate=3.9),
            '30-year tenor': lambda r: r['ust_par_yield']['tenors'].pop('30'),
            'number of years': lambda r: r['ust_par_yield']['tenors'].update({'ten': 0.05}),
            'must equal market inputs': lambda r: r.update(valuation_date='2026-10-23'),
            'unexpected': lambda r: r.update(estr=0.02),
            'use as_of null': lambda r: r['eurusd']['source'].update(as_of='2026-10-22'),
            'USD per EUR': lambda r: r['eurusd'].update(rate=0.01),
            'schema_version': lambda r: r.update(schema_version=2),
        }
        for message, change in cases.items():
            data = copy.deepcopy(self.rates)
            change(data)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                inputs.load(market, self.write('r.json', data))
        self.rates['kind'] = 'user_supplied'
        self.rates['sofr']['source'].update(as_of='2026-10-23', fetched_utc='2026-10-23T12:00:00Z')
        with self.assertRaisesRegex(ValueError, 'sofr observation 2026-10-23 is after valuation_date 2026-10-22'):
            rates.load(self.write('r.json', self.rates))

    def test_dates_outside_terms_coverage_are_rejected(self):
        for day, message in (('2026-10-20', 'precedes the 2026-10-21 contract-terms snapshot'),
                             ('2028-09-15', 'on or after the 2028 note maturity')):
            self.market['valuation_date'] = self.rates['valuation_date'] = day
            with self.subTest(day=day), self.assertRaisesRegex(ValueError, message):
                run.note_scenarios(20, inputs.load(self.write('m.json', self.market), self.write('r.json', self.rates)))

    def test_supplied_note_assumption_is_priced_and_grid_is_unchanged(self):
        with_own = inputs.load(self.write('m.json', self.market), self.write('r.json', self.rates))
        self.market.pop('note_assumptions')
        without = inputs.load(self.write('m2.json', self.market), self.write('r.json', self.rates))
        a, b = run.note_scenarios(60, with_own), run.note_scenarios(60, without)
        for own, plain in zip(a['notes'], b['notes']):
            self.assertEqual(own['scenarios'], plain['scenarios'])
            self.assertIsNone(plain['supplied_assumption'])
        row = next(n for n in a['notes'] if n['terms']['name'] == '2029')
        cb = notes.to_convertible('2029', notes._d('2026-10-22'))
        expected = price(cb, 250, 0.55, row['risk_free_cc_proxy'], spread=0.04, steps=60).value
        self.assertEqual(row['supplied_assumption']['value_per_1000_usd'], expected)
        self.assertEqual((row['supplied_assumption']['vol_assumption'], row['supplied_assumption']['spread_assumption']),
                         (0.55, 0.04))
        self.assertNotIn(expected, [s['value_per_1000_usd'] for s in row['scenarios']])

    def test_note_assumptions_reject_percent_units_and_unknown_notes(self):
        rates_path = self.write('r.json', self.rates)
        cases = {'60% volatility is 0.6': lambda m: m['note_assumptions']['2029'].update(volatility=55),
                 '500 bp spread is 0.05': lambda m: m['note_assumptions']['2029'].update(credit_spread=4),
                 'subset of': lambda m: m['note_assumptions'].update({'2040': m['note_assumptions']['2029']}),
                 'requires volatility': lambda m: m['note_assumptions']['2029'].pop('source')}
        for message, change in cases.items():
            data = copy.deepcopy(self.market)
            change(data)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                inputs.load(self.write('m.json', data), rates_path)

    def test_default_run_keeps_the_frozen_snapshot_and_prints_a_summary(self):
        code, text, out = self.cli()
        self.assertEqual(code, 0)
        preferred = json.loads((out / 'preferred.json').read_text())
        self.assertEqual(preferred['as_of'], '2026-10-21')
        self.assertEqual(preferred['market_inputs']['rates'],
                         {'kind': 'frozen_public_snapshot', 'valuation_date': '2026-10-21', 'input_sha256': None})
        for expected in ('SYNTHETIC', 'MSTR spot $250.00', 'conversion price $1,000.00', 'parity $25.00',
                         'STRF    $100.00  10.38%', '2029   $672.40'):
            self.assertIn(expected, text)


    def test_readme_table_is_generated_from_saved_results(self):
        readme = (inputs.ROOT / 'README.md').read_text()
        block = readme.split('<!-- preferred-summary:start -->\n', 1)[1].split('\n<!-- preferred-summary:end -->', 1)[0]
        saved = json.loads((inputs.ROOT / 'results/preferred.json').read_text())
        self.assertEqual(block, summary.markdown(saved))
        self.assertIn('Price (synthetic)', block)


if __name__ == '__main__':
    unittest.main()
