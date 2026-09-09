import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from scripts.build_weekly import CarrierResolver, main


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
                'Customer': [self.names[0], self.names[0], None],
                'Provider': ['Voicekings-Tec', 'Voicekings-Tec', None],
                'Sell Destination': ['France', 'France', None],
                'Duration (m)': [10, 20, 30], 'Revenue': [20, 40, 60],
                'Expense': [10, 20, 30], 'Profit': [10, 20, 30]})
            gross.to_csv(source / 'gross.csv', index=False)
            gross.to_csv(source / 'duplicate.csv', index=False)
            output = root / 'out'
            log = io.StringIO()
            with contextlib.redirect_stdout(log):
                main(str(root / 'exports'), str(output))
            def read(name):
                with (output / (name + '.csv')).open(newline='', encoding='utf-8') as f:
                    return list(csv.DictReader(f))
            carriers = {r['name']: r for r in read('carriers')}
            self.assertEqual(set(carriers), set(self.names))
            self.assertEqual(carriers[self.names[0]]['am'], 'Nour Ahmad')
            self.assertEqual(carriers[self.names[1]]['am'], 'Mostafa zreik')
            self.assertEqual(float(carriers[self.names[0]]['rev']), 60)
            self.assertEqual(read('providers')[0]['name'], self.names[1])
            self.assertEqual(read('customers')[0]['name'], self.names[0])
            self.assertEqual(read('routes')[0]['provider'], self.names[1])
            self.assertEqual(read('customer_routes')[0]['destination'], 'France')
            self.assertEqual({r['name'] for r in read('am_breakdown')}, set(self.names))
            self.assertEqual({r['carrier'] for r in read('daily_carrier')}, set(self.names))
            self.assertEqual({r['day'] for r in read('daily_carrier')},
                             {'2026-08-01', '2026-09-01'})
            self.assertIn('Authoritative roster: 2 carriers', log.getvalue())


if __name__ == '__main__':
    unittest.main()
