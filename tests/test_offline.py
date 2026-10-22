"""Exercise restoration and the actual CLI without a network connection."""
import contextlib
import io
import json
import math
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
                differences = []
                self.assert_reference(json.loads(body), json.loads((ROOT / 'results' / name).read_bytes()),
                                      name, differences)
                if differences:
                    print(f'\n{name}: {len(differences)} platform float differences within rtol=1e-12/atol=1e-10')
                    for path, actual, expected in differences[:8]:
                        print(f'{path}: actual={actual:.17g}, reference={expected:.17g}, delta={actual-expected:.3g}')
                    largest = max(differences, key=lambda d: abs(d[1] - d[2]))
                    print(f'Largest absolute delta: {largest[0]} = {abs(largest[1]-largest[2]):.3g}')
            self.assertEqual(len(json.loads(first['preferred.json'])['rows']), 5)
            notes = json.loads(first['convertibles.json'])['notes']
            self.assertEqual(len(notes), 6)
            self.assertTrue(all(len(n['scenarios']) == 9 for n in notes))

    def assert_reference(self, actual, expected, path, differences):
        self.assertIs(type(actual), type(expected), f'{path}: JSON type changed')
        if isinstance(actual, dict):
            self.assertEqual(actual.keys(), expected.keys(), f'{path}: keys changed')
            for key in actual:
                self.assert_reference(actual[key], expected[key], f'{path}.{key}', differences)
        elif isinstance(actual, list):
            self.assertEqual(len(actual), len(expected), f'{path}: count changed')
            for i, (left, right) in enumerate(zip(actual, expected)):
                self.assert_reference(left, right, f'{path}[{i}]', differences)
        elif isinstance(actual, float):
            self.assertTrue(math.isfinite(actual) and math.isfinite(expected), f'{path}: nonfinite value')
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-10),
                            f'{path}: actual={actual:.17g}, reference={expected:.17g}, delta={actual-expected:.3g}')
            if actual != expected:
                differences.append((path, actual, expected))
        else:
            self.assertEqual(actual, expected, f'{path}: exact value changed')

    def test_reference_check_rejects_meaningful_numeric_and_schema_changes(self):
        differences = []
        self.assert_reference({'price': math.nextafter(1000.0, math.inf)}, {'price': 1000.0}, '$', differences)
        self.assertEqual(len(differences), 1)
        for actual, expected in (({'price': 1000.01}, {'price': 1000.0}),
                                 ({'price': 1000}, {'price': 1000.0}),
                                 ({'kind': 'observed'}, {'kind': 'synthetic'}),
                                 ({'rows': [1]}, {'rows': [1, 2]})):
            with self.subTest(actual=actual), self.assertRaises(AssertionError):
                self.assert_reference(actual, expected, '$', [])

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
