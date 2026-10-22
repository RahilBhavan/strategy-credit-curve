"""Exercise restoration and the actual CLI without a network connection."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from credit_curve import run
from scripts import restore_data

ROOT = Path(__file__).resolve().parents[1]


class OfflineWorkflow(unittest.TestCase):
    def test_cli_is_offline_repeatable_and_matches_reviewed_results(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')), \
             patch('sys.argv', ['credit_curve.run', '--out', tmp]), \
             contextlib.redirect_stdout(io.StringIO()):
            run.main()
            first = {p.name: p.read_bytes() for p in Path(tmp).glob('*.json')}
            run.main()
            self.assertEqual(first, {p.name: p.read_bytes() for p in Path(tmp).glob('*.json')})
            for name, body in first.items():
                self.assertEqual(json.loads(body), json.loads((ROOT / 'results' / name).read_bytes()))
            self.assertEqual(len(json.loads(first['preferred.json'])['rows']), 5)
            notes = json.loads(first['convertibles.json'])['notes']
            self.assertEqual(len(notes), 6)
            self.assertTrue(all(len(n['scenarios']) == 9 for n in notes))

    def test_invalid_steps_exit_before_writing_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'absent'
            for steps in ('-1', '1', '10001', 'nan'):
                with self.subTest(steps=steps), \
                     patch('sys.argv', ['credit_curve.run', '--out', str(out), '--steps', steps]), \
                     contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    run.main()
                self.assertEqual(error.exception.code, 2)
                self.assertFalse(out.exists())

    def test_restore_is_repeatable_and_refuses_changed_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen = root / 'frozen'
            frozen.mkdir()
            body = b'independently authored test fixture'
            (frozen / 'fixture.gz').write_bytes(restore_data.gzip.compress(body))
            item = {'path': 'data/fixture', 'bytes': len(body),
                    'sha256': restore_data.hashlib.sha256(body).hexdigest(), 'parts': ['fixture.gz']}
            (frozen / 'index.json').write_text(json.dumps([item]))
            with patch.object(restore_data, 'FROZEN', frozen):
                self.assertEqual(restore_data.restore(root), 1)
                self.assertEqual(restore_data.restore(root), 1)
                path = root / item['path']
                path.write_bytes(b'changed source')
                with self.assertRaisesRegex(ValueError, 'refusing to overwrite'):
                    restore_data.restore(root)
                self.assertEqual(path.read_bytes(), b'changed source')

    def test_restore_rejects_corruption_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen = root / 'frozen'
            frozen.mkdir()
            (frozen / 'fixture.gz').write_bytes(restore_data.gzip.compress(b'fixture'))
            (frozen / 'index.json').write_text(json.dumps([
                {'path': 'data/fixture', 'bytes': 7, 'sha256': 'incorrect', 'parts': ['fixture.gz']}
            ]))
            with patch.object(restore_data, 'FROZEN', frozen), \
                 self.assertRaisesRegex(ValueError, 'hash mismatch'):
                restore_data.restore(root)
            self.assertFalse((root / 'data/fixture').exists())
