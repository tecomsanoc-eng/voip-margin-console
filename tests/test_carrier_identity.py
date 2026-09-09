import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from scripts.build_weekly import CarrierResolver, main, norm, load_reviewed_aliases, DEFAULT_ALIASES


class CarrierIdentityTests(unittest.TestCase):
    def setUp(self):
        self.names = ['Voicekings Offshore S.A.L', 'Tec-Voicekings Offshore S.A.L']
        self.details = pd.DataFrame({
            'Carrier Name': self.names,
            'Carrier Account Manager': ['n.ahmad', 'm.zreik'],
            'Carrier Type': ['Both', 'Both']})
        self.exposure = pd.DataFrame({
            'Carrier': self.names, 'Carrier Id': ['101', '102'],
            'Account Manager': ['Nour Ahmad', 'Mostafa zreik'],
            'Current Exposure': [10, 20]})

    def test_roster_and_marker_reordering(self):
        resolver = CarrierResolver(self.details, self.exposure)
        self.assertEqual(len(resolver.names), 2)
        self.assertNotEqual(*(resolver.roster_key(n) for n in self.names))
        self.assertEqual(resolver.resolve('Voicekings-Tec')[0], 'exposure:102')
        pairs = [('VoiceLynx-tec', 'tec-VoiceLynx'),
                 ('Global Voice SRL-Tec', 'Tec-Global Voice SRL'),
                 ('Tec-VoiceTec', 'VoiceTec-Tec')]
        for alias, name in pairs:
            resolver = CarrierResolver(pd.DataFrame({'Carrier Name': [name]}))
            self.assertEqual(resolver.resolve(alias)[0], resolver.roster_key(name))

    def test_ambiguity_and_meaningful_markers(self):
        resolver = CarrierResolver(pd.DataFrame({'Carrier Name': [
            'Example Voice Ltd', 'Example Voice LLC', 'Example Voice-Tec',
            'Example Voice-Com', 'Example Voice-Loc']}))
        identity, candidates = resolver.resolve('Example Voice')
        self.assertIsNone(identity)
        self.assertEqual(set(candidates), {'Example Voice Ltd', 'Example Voice LLC'})
        self.assertIsNotNone(resolver.resolve('Tec-Example Voice')[0])
        self.assertEqual(resolver.resolve('Example Voice Ltd')[0],
                         resolver.roster_key('Example Voice Ltd'))
        self.assertIsNone(resolver.resolve('Completely Unknown')[0])
        fuzzy = CarrierResolver(pd.DataFrame({'Carrier Name': [
            'Longcarrier Alpha', 'Longcarrier Alphab']}))
        self.assertIsNone(fuzzy.resolve('Longcarrier Alph')[0])
        self.assertEqual(len(fuzzy.resolve('Longcarrier Alph')[1]), 2)

    def test_marker_formats_and_legal_suffixes(self):
        for marker in ('TEC', 'COM', 'LOC'):
            name = marker + '-Example Voice Co. LLC'
            resolver = CarrierResolver(pd.DataFrame({'Carrier Name': [name]}))
            for alias in ('Example Voice-' + marker, marker + '-Example Voice',
                          'Example Voice_' + marker, 'Example Voice ' + marker,
                          'Example Voice.' + marker, 'Example Voice - ' + marker):
                with self.subTest(alias=alias):
                    self.assertEqual(resolver.resolve(alias)[0], resolver.roster_key(name))
            self.assertIsNone(resolver.resolve('Example Voice')[0])
            self.assertIsNone(resolver.resolve('ExampleVoiceTEC')[0])

    def test_meaningful_words_and_unique_whole_word_prefix(self):
        self.assertEqual(norm('Global Telecom Communications Networks Services Carrier Co.'),
                         'global telecom communications networks services carrier')
        names = ['Tec-Digital Cloud Communications', 'Tec-Stream Telecom', 'Tec-Stream-iT']
        resolver = CarrierResolver(pd.DataFrame({'Carrier Name': names}))
        self.assertEqual(resolver.resolve('Digital_Cloud.TEC')[0], resolver.roster_key(names[0]))
        self.assertIsNone(resolver.resolve('Cloud-Tec')[0])
        self.assertIsNone(resolver.resolve('Digital Cloud-COM')[0])
        identity, candidates = resolver.resolve('Stream-Tec')
        self.assertIsNone(identity)
        self.assertEqual(set(candidates), set(names[1:]))
        # Whole meaningful words still distinguish otherwise similar carriers.
        resolver = CarrierResolver(pd.DataFrame({'Carrier Name': [
            'Tec-Digital Cloud Communications', 'Tec-Digital Cloud Networks']}))
        self.assertEqual(len(resolver.resolve('Digital Cloud-Tec')[1]), 2)
        resolver = CarrierResolver(pd.DataFrame({'Carrier Name': ['Tec-382 Communications']}))
        self.assertIsNone(resolver.resolve('382-Tec')[0])
        self.assertEqual(len(resolver.resolve('382-Tec')[1]), 1)

    def test_equivalent_formats_cannot_hide_ambiguity(self):
        names = ['Tec-Example Voice Ltd', 'ExampleVoice-Tec LLC']
        resolver = CarrierResolver(pd.DataFrame({'Carrier Name': names}))
        identity, candidates = resolver.resolve('Tec-Example Voice')
        self.assertIsNone(identity)
        self.assertEqual(set(candidates), set(names))
        self.assertEqual(resolver.resolve(names[0])[0], resolver.roster_key(names[0]))

    def test_source_diagnostics_and_transaction_only_carriers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'exports'
            source.mkdir()
            details = pd.concat([self.details, pd.DataFrame({'Carrier Name': [
                'Tec-Stream Telecom', 'Tec-Stream-iT']})], ignore_index=True)
            details.to_csv(source / 'details.csv', index=False)
            self.exposure.to_csv(source / 'exposure.csv', index=False)
            pd.DataFrame({
                'Date': ['2026-09-01'] * 4, 'Customer': [self.names[1]] * 4,
                'Provider': ['Unknown Active-Tec', 'Unknown Zero-Tec', 'Stream-Tec', 'Shared Unknown-Tec'],
                'Revenue': [10, 0, 20, 30], 'Expense': [5, 0, 10, 15],
                'Profit': [5, 0, 10, 15], 'Duration (m)': [1, 0, 2, 3],
                'Sell Destination': ['France'] * 4}).to_csv(source / 'gross.csv', index=False)
            pd.DataFrame({
                'Customer': [self.names[1]] * 3,
                'Provider': ['Full Active-Tec', 'Shared Unknown-Tec', 'Full Zero-Tec'],
                'Destination': ['France'] * 3, 'IG ASR (%)': [50, 50, 0],
                'Duration (min)': [4, 5, 0]}).to_csv(source / 'full.csv', index=False)
            (source / 'lcr.csv').write_text('Unrecognized header\nLCR placeholder\n')
            lcr = pd.DataFrame({'dest': ['France'] * 3,
                                'provider': ['LCR Only-Tec', 'Shared Unknown-Tec', 'Voicekings-Tec'],
                                'trunk': ['a', 'b', 'c'], 'vol': [100] * 3, 'rate': [.1] * 3})
            log = io.StringIO()
            with patch('scripts.build_weekly.load_lcr', return_value=lcr), contextlib.redirect_stdout(log):
                main(str(source), str(root / 'out'), alias_path=None)
            with (root / 'out' / 'carriers.csv').open(newline='') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual({r['name'] for r in rows}, (set(details['Carrier Name']) - {self.names[0]}) |
                             {'Unknown Active-Tec', 'Shared Unknown-Tec', 'Full Active-Tec'})
            self.assertEqual(sum(float(r['rev']) for r in rows), 60)
            for line in ('unresolved [LCR]: LCR Only-Tec',
                         'unresolved [Gross,Full,LCR]: Shared Unknown-Tec',
                         'unresolved [Full]: Full Active-Tec',
                         'unresolved [Gross]: Stream-Tec | candidates:',
                         'LCR-only unresolved: 1', 'Gross/Full unresolved: 6',
                         'Output carriers: 6'):
                self.assertIn(line, log.getvalue())

    def test_reviewed_aliases_and_gtk(self):
        approved = load_reviewed_aliases(DEFAULT_ALIASES)
        self.assertEqual(len(approved), 6)
        names = [r['authoritative_name'] for r in approved] + [
            'TEC_GESTIONES TECNICAS KASTA COSTASOL S.L.,',
            'FN Telecom LLC', 'Tec-Quickcom Telecom Limited OLD',
            'Tec-Quickcom Telecom Limited-Deleted']
        resolver = CarrierResolver(pd.DataFrame({'Carrier Name': names}), reviewed_aliases=approved)
        for row in approved:
            with self.subTest(alias=row['alias']):
                self.assertEqual(resolver.resolve(row['alias'])[0],
                                 resolver.roster_key(row['authoritative_name']))
                self.assertTrue(resolver.is_tec_alias(row['alias']))
        self.assertEqual(len(resolver.names), len(names))
        self.assertIsNone(resolver.resolve('GTK TELECOM-TEC')[0])
        self.assertIsNone(resolver.resolve('FN_tc')[0])
        self.assertFalse(resolver.is_tec_alias('FN_tc'))
        self.assertFalse(resolver.is_tec_alias('Technical Services'))
        self.assertFalse(resolver.is_tec_alias('VoiceTec'))
        self.assertFalse(resolver.is_tec_alias('FN Telecom LLC'))

    def test_reviewed_alias_validation(self):
        names = ['Tec-Example', 'Tec-Another', 'Technical Services', 'Example-COM']
        details = pd.DataFrame({'Carrier Name': names})
        cases = [([{'alias': 'short', 'authoritative_name': 'Absent-Tec'}], 'missing'),
                 ([{'alias': 'short', 'authoritative_name': 'Technical Services'}], 'TEC-related'),
                 ([{'alias': 'short', 'authoritative_name': 'Example-COM'}], 'TEC-related'),
                 ([{'alias': 'short', 'authoritative_name': 'Tec-Example'},
                   {'alias': 'short', 'authoritative_name': 'Tec-Another'}], 'multiple'),
                 ([{'alias': 'Tec-Another', 'authoritative_name': 'Tec-Example'}], 'merge')]
        for aliases, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                CarrierResolver(details, reviewed_aliases=aliases)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'aliases.csv'
            path.write_text('alias,wrong_column\nshort,Tec-Example\n')
            with self.assertRaisesRegex(ValueError, 'columns'):
                load_reviewed_aliases(path)

    def test_mixed_traffic_filters_every_production_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'exports'
            source.mkdir()
            self.details.to_csv(source / 'details.csv', index=False)
            self.exposure.to_csv(source / 'exposure.csv', index=False)
            pd.DataFrame({
                'Date': ['2026-08-01', '2026-09-01'],
                'Customer': [self.names[0], 'Voicekings-Tec'],
                'Provider': ['Voicekings-Tec', self.names[0]],
                'Revenue': [20, 40], 'Expense': [10, 25], 'Profit': [10, 15],
                'Duration (m)': [1, 2], 'Sell Destination': ['France', 'France']
            }).to_csv(source / 'gross.csv', index=False)
            with contextlib.redirect_stdout(io.StringIO()):
                main(str(source), str(root / 'out'), alias_path=None)
            outputs = {}
            for path in (root / 'out').glob('*.csv'):
                with path.open(newline='', encoding='utf-8') as f:
                    outputs[path.stem] = list(csv.DictReader(f))
                for row in outputs[path.stem]:
                    for field in ('name', 'carrier', 'customer', 'provider'):
                        if field in row:
                            self.assertEqual(row[field], self.names[1])
            self.assertEqual(len(outputs['carriers']), 1)
            self.assertEqual(outputs['carriers'][0]['am'], 'Mostafa zreik')
            self.assertEqual(float(outputs['carriers'][0]['rev']), 40)
            self.assertEqual(float(outputs['carriers'][0]['exp']), 10)
            self.assertEqual(len(outputs['routes']), 1)
            self.assertEqual(outputs['customer_routes'], [])
            self.assertEqual(len(outputs['daily_carrier']), 2)
            # The non-TEC master identity still resolves independently.
            resolver = CarrierResolver(self.details, self.exposure)
            self.assertEqual(resolver.resolve(self.names[0])[0], 'exposure:101')
            self.assertEqual(self.exposure.iloc[0]['Account Manager'], 'Nour Ahmad')

    def test_sanity_checks(self):
        duplicate_id = self.exposure.copy()
        duplicate_id['Carrier Id'] = '101'
        with self.assertRaisesRegex(ValueError, 'collapse'):
            CarrierResolver(self.details, duplicate_id)
        resolver = CarrierResolver(self.details, self.exposure)
        with self.assertRaises(ValueError):
            resolver.validate([], [])
        with self.assertRaises(ValueError):
            resolver.validate(resolver.names, [{'name': self.names[0]}] * 2)

    def test_pipeline_preserves_roster_ownership_and_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'exports' / 'nested'
            source.mkdir(parents=True)
            self.details.to_csv(source / 'details.csv', index=False)
            self.exposure.to_csv(source / 'exposure.csv', index=False)
            gross = pd.DataFrame({
                'Date': ['2026-08-01', '2026-09-01', None],
                'Customer': [self.names[1], self.names[1], None],
                'Provider': ['Voicekings-Tec', 'Voicekings-Tec', None],
                'Sell Destination': ['France', 'France', None],
                'Duration (m)': [10, 20, 30], 'Revenue': [20, 40, 60],
                'Expense': [10, 20, 30], 'Profit': [10, 20, 30]})
            gross.to_csv(source / 'gross.csv', index=False)
            gross.to_csv(source / 'duplicate.csv', index=False)
            output = root / 'out'
            log = io.StringIO()
            with contextlib.redirect_stdout(log):
                main(str(root / 'exports'), str(output), alias_path=None)
            def read(name):
                with (output / (name + '.csv')).open(newline='', encoding='utf-8') as f:
                    return list(csv.DictReader(f))
            carriers = {r['name']: r for r in read('carriers')}
            self.assertEqual(set(carriers), {self.names[1]})
            self.assertNotIn(self.names[0], carriers)
            self.assertEqual(carriers[self.names[1]]['am'], 'Mostafa zreik')
            self.assertEqual(float(carriers[self.names[1]]['rev']), 60)
            self.assertEqual(read('providers')[0]['name'], self.names[1])
            self.assertEqual(read('customers')[0]['name'], self.names[1])
            self.assertEqual(read('routes')[0]['provider'], self.names[1])
            self.assertEqual(read('customer_routes')[0]['destination'], 'France')
            self.assertEqual({r['name'] for r in read('am_breakdown')}, {self.names[1]})
            self.assertEqual({r['carrier'] for r in read('daily_carrier')}, {self.names[1]})
            self.assertEqual({r['day'] for r in read('daily_carrier')},
                             {'2026-08-01', '2026-09-01'})
            self.assertIn('Master authoritative roster: 2', log.getvalue())


if __name__ == '__main__':
    unittest.main()
