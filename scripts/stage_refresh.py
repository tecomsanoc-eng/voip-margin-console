"""Replace only staging tables, then verify every row against validated CSVs."""
import argparse
import json
import math
from pathlib import Path
from import_csv import SCHEMA, read_csv
from seed_supabase import BATCH, load_config, request


def fetch_rows(url, key, table, pk):
    rows = []
    while True:
        page = json.loads(request(url, key, 'GET',
            '%s?select=*&order=%s&limit=1000&offset=%d' % (table, pk, len(rows))))
        if not page:
            return rows
        rows.extend(page)


def verify_rows(expected, actual, pk):
    if len(expected) != len(actual):
        raise ValueError('Read-back row count mismatch')
    indexed = {r[pk]: r for r in actual}
    if len(indexed) != len(actual):
        raise ValueError('Duplicate staging primary key')
    for row in expected:
        other = indexed.get(row[pk])
        if other is None:
            raise ValueError('Missing staging primary key')
        for column, value in row.items():
            found = other.get(column)
            equal = (isinstance(found, (int, float)) and math.isclose(value, found, rel_tol=1e-12, abs_tol=1e-9)
                     if isinstance(value, (int, float)) else value == found)
            if not equal:
                raise ValueError('Staging value mismatch: %s / %s' % (row[pk], column))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory', type=Path)
    ap.add_argument('--load', action='store_true', help='replace all eight _next tables; default is read-only verification')
    args = ap.parse_args()
    datasets = {t: read_csv(t, args.directory / (t + '.csv')) for t in SCHEMA}
    carriers = {r['name'] for r in datasets['carriers'][0]}
    if len(carriers) != 419:
        raise ValueError('This reviewed refresh requires 419 carriers')
    for table, (rows, pk) in datasets.items():
        for row in rows:
            for col in ('name', 'carrier', 'customer', 'provider'):
                if col in row and row[col] not in carriers:
                    raise ValueError('Identity outside approved carrier roster: %s' % row[col])
    url, key = load_config()
    if args.load:
        for table, (rows, pk) in datasets.items():
            # PKs cannot be null: covers all existing keys, including negative ids.
            request(url, key, 'DELETE', table + '_next?' + pk + '=not.is.null')
            for start in range(0, len(rows), BATCH):
                request(url, key, 'POST', table + '_next', rows[start:start+BATCH])
            print(table + '_next replaced: ' + str(len(rows)), flush=True)
    for table, (rows, pk) in datasets.items():
        actual = fetch_rows(url, key, table + '_next', pk)
        verify_rows(rows, actual, pk)
        print('%s_next: %d rows; all fields and primary keys verified' % (table, len(actual)), flush=True)
    print('Staging verification PASSED. No live tables written.')


if __name__ == '__main__':
    main()
