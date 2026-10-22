"""Real-source contracts, frozen hashes, stock split and comparison output."""
import hashlib
import json
import math
import pathlib
import unittest

from credit_curve import curve, fetch, notes
from credit_curve.text import html_to_text, squash

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Sources(unittest.TestCase):
    def test_manifest_hashes(self):
        for rel, row in fetch.manifest().items():
            with self.subTest(rel=rel):
                self.assertTrue(row['url'].startswith('https://'))
                self.assertEqual(hashlib.sha256((fetch.RAW / rel).read_bytes()).hexdigest(), row['sha256'])

    def test_six_note_current_rates_reconcile_to_issue_and_split(self):
        initial = {'2028': 5.4589, '2029': 1.4872, '2030A': 0.6677,
                   '2030B': 2.3072, '2031': 0.4297, '2032': 0.4894}
        for name, old in initial.items():
            t = notes.terms(name)
            factor = 10 if name in ('2030A', '2031', '2032') else 1
            self.assertAlmostEqual(t['ratio'], old * factor, delta=0.000001)
            self.assertAlmostEqual(t['conversion_price'] * t['ratio'], 1000)
            self.assertLess(t['put_date'], t['maturity'])
        self.assertAlmostEqual(sum(notes.terms(n)['principal'] for n in notes.NAMES), 6713659000)

    def test_term_quotes_exist_in_their_primary_filings(self):
        cache = {}
        for sheet in (curve.termsheet(), notes.termsheet()):
            for ticker, terms in sheet.items():
                if not isinstance(terms, dict):
                    continue
                for field, datum in terms.items():
                    if not isinstance(datum, dict) or 'source' not in datum or 'quote' not in datum:
                        continue
                    rel = datum['source']
                    if not isinstance(rel, str):
                        continue
                    if rel not in cache:
                        cache[rel] = squash(html_to_text((ROOT / rel).read_bytes()))
                    with self.subTest(ticker=ticker, field=field):
                        self.assertIn(squash(datum['quote']), cache[rel])

    def test_five_instrument_comparison_has_distinct_rights_and_fx(self):
        r = curve.build()
        by = {x['ticker']: x for x in r['rows']}
        self.assertEqual(list(by), ['STRF', 'STRC', 'STRE', 'STRK', 'STRD'])
        self.assertFalse(by['STRD']['cumulative'])
        self.assertTrue(all(by[t]['cumulative'] for t in ('STRF', 'STRC', 'STRE', 'STRK')))
        self.assertEqual(by['STRK']['conversion_rate'], 0.1)
        self.assertEqual(by['STRC']['payments_per_year'], 24)
        self.assertTrue(by['STRE']['price_is_synthetic'])
        self.assertIsNone(by['STRE']['price_is_stale'])
        self.assertFalse(any(x['live_ranking_eligible'] for x in r['rows']))
        self.assertEqual(r['market_inputs']['kind'], 'synthetic_scenario')
        self.assertEqual(by['STRE']['currency'], 'EUR')
        self.assertGreater(by['STRE']['usd_price_at_reference_fx'], 0)
        self.assertIn('pending', r['daily_dividend_amendment'])
        for x in r['rows']:
            self.assertTrue(math.isfinite(x['spread_bp']))
        self.assertEqual(json.dumps(r, sort_keys=True), json.dumps(curve.build(), sort_keys=True))
