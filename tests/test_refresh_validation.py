import tempfile
import unittest
from pathlib import Path
from scripts.import_csv import read_csv
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from stage_refresh import verify_rows

class RefreshValidationTests(unittest.TestCase):
    def test_duplicate_csv_keys_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'totals.csv'
            p.write_text('am,total_carriers\nA,1\nA,2\n')
            with self.assertRaisesRegex(SystemExit, 'duplicate primary key'):
                read_csv('am_totals', p)
    def test_invalid_numeric_values_fail(self):
        for value in ('NaN', 'inf', '1.5'):
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / 'totals.csv'
                p.write_text('am,total_carriers\nA,' + value + '\n')
                with self.assertRaises(SystemExit):
                    read_csv('am_totals', p)
    def test_readback_detects_corruption_even_with_same_count(self):
        expected = [{'name': 'Tec-A', 'am': 'Owner', 'rev': 12.3}]
        verify_rows(expected, expected, 'name')
        for actual in ([dict(expected[0], am='Wrong')], [dict(expected[0], name='Tec-B')], []):
            with self.assertRaises(ValueError):
                verify_rows(expected, actual, 'name')
    def test_readback_detects_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            verify_rows([{'id': 1}, {'id': 2}], [{'id': 1}, {'id': 1}], 'id')
