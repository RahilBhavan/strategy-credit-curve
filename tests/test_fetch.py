"""Offline failure/retry checks for the optional source fetcher."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from credit_curve import fetch, market_fetch


class FetchFailures(unittest.TestCase):
    def test_market_fetch_reports_failure_to_caller(self):
        with patch.object(market_fetch, 'urls', return_value={'missing.json': 'https://example.test/data'}), \
             patch.object(fetch, 'get', side_effect=RuntimeError('unavailable')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(market_fetch.main('2026-10-21'), 1)

    def test_rate_limit_retry_persists_one_verified_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            response = unittest.mock.MagicMock()
            response.__enter__.return_value.read.return_value = b'public fixture'
            error = HTTPError('https://example.test/data', 429, 'rate limit', {}, None)
            self.addCleanup(error.close)
            with patch.object(fetch, 'RAW', raw), patch.object(fetch, 'MANIFEST', raw / 'manifest.csv'), \
                 patch.object(fetch.urllib.request, 'urlopen', side_effect=[error, response]) as request, \
                 patch.object(fetch.time, 'sleep'):
                self.assertEqual(fetch.get('https://example.test/data', 'fixture.txt'), b'public fixture')
                self.assertEqual(fetch.get('https://example.test/data', 'fixture.txt'), b'public fixture')
                self.assertEqual(request.call_count, 2)
                self.assertEqual(list(fetch.manifest()), ['fixture.txt'])
                self.assertEqual(fetch.manifest()['fixture.txt']['sha256'],
                                 fetch.hashlib.sha256(b'public fixture').hexdigest())

    def test_failed_retries_leave_prior_cache_and_manifest_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / 'fixture.txt').write_bytes(b'original')
            (raw / 'manifest.csv').write_bytes(b'original manifest')
            error = HTTPError('https://example.test/data', 503, 'unavailable', {}, None)
            self.addCleanup(error.close)
            with patch.object(fetch, 'RAW', raw), patch.object(fetch, 'MANIFEST', raw / 'manifest.csv'), \
                 patch.object(fetch.urllib.request, 'urlopen', side_effect=error) as request, \
                 patch.object(fetch.time, 'sleep'):
                with self.assertRaises(RuntimeError):
                    fetch.get('https://example.test/data', 'fixture.txt', refresh=True)
                self.assertEqual(request.call_count, 3)
                self.assertEqual((raw / 'fixture.txt').read_bytes(), b'original')
                self.assertEqual((raw / 'manifest.csv').read_bytes(), b'original manifest')
