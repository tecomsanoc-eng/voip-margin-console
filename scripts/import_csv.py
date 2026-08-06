"""Load a CSV into one of the console tables.

This is the repeatable path for the monthly billing refresh: export from the
billing system, shape it into one CSV per table, then run this once per file.

    python scripts\\import_csv.py routes exports\\routes.csv
    python scripts\\import_csv.py --append daily_carrier exports\\aug.csv

By default the target table is emptied first. Use --append to add to it, which
is what you want for daily_carrier when loading a new month.

The CSV must have a header row whose names match the columns listed in SCHEMA
below. Extra columns are rejected rather than silently dropped, because a
mis-mapped column here becomes a wrong margin on the dashboard.
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from seed_supabase import BATCH, load_config, request, clear  # noqa: E402

# column name -> parser. Order is documentation only; CSV is matched by header.
NUM = "num"
INT = "int"
TXT = "txt"

SCHEMA = {
    "providers": ("name", {
        "name": TXT, "am": TXT, "exposure": NUM, "credit": NUM,
        "terms": TXT, "conf": TXT}),
    "customers": ("name", {
        "name": TXT, "am": TXT, "exposure": NUM, "credit": NUM,
        "terms": TXT, "conf": TXT}),
    "carriers": ("name", {
        "name": TXT, "role": TXT, "am": TXT, "dur": NUM, "calls": INT,
        "rev": NUM, "profit": NUM, "due": TXT, "netbal": NUM,
        "curexp": NUM, "exp": NUM}),
    "routes": ("id", {
        "id": INT, "destination": TXT, "provider": TXT, "trunk": TXT,
        "lcr": NUM, "buy": NUM, "sell": NUM, "profit": NUM,
        "profit_pct": NUM, "asr": NUM, "acd": NUM, "calls": INT, "dur": NUM}),
    "customer_routes": ("id", {
        "id": INT, "customer": TXT, "destination": TXT, "provider": TXT,
        "sell": NUM, "buy": NUM, "profit": NUM, "profit_pct": NUM,
        "asr": NUM, "acd": NUM, "calls": INT, "dur": NUM,
        "rev": NUM, "exp": NUM}),
    "am_breakdown": ("id", {
        "id": INT, "am": TXT, "side": TXT, "name": TXT, "profit": NUM,
        "calls": INT, "dur": NUM, "rev": NUM, "exp": NUM,
        "routes": INT, "sec": INT}),
    "am_totals": ("am", {"am": TXT, "total_carriers": INT}),
    "daily_carrier": ("id", {
        "id": INT, "carrier": TXT, "day": TXT, "cust_rev": NUM,
        "cust_profit": NUM, "cust_dur": NUM, "cust_calls": INT,
        "prov_exp": NUM, "prov_profit": NUM, "prov_dur": NUM,
        "prov_calls": INT}),
}


def coerce(value, kind, table, column, line_no):
    value = (value or "").strip()
    if value == "":
        return None
    if kind == TXT:
        # Only blanks count as null for text. The carrier list genuinely
        # contains an entry named "N/A", so placeholder tokens must be taken
        # literally here or a real row silently loses its primary key.
        return value
    if value.upper() in ("NULL", "NA", "N/A", "-", "--"):
        return None
    cleaned = value.replace(",", "").replace("%", "")
    try:
        return int(float(cleaned)) if kind == INT else float(cleaned)
    except ValueError:
        sys.exit("%s line %d: column '%s' has non-numeric value %r"
                 % (table, line_no, column, value))


def read_csv(table, path):
    pk, columns = SCHEMA[table]

    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            sys.exit("%s appears to be empty." % path)

        headers = [h.strip() for h in reader.fieldnames]
        unknown = [h for h in headers if h not in columns]
        missing = [c for c in columns if c not in headers]
        if unknown:
            sys.exit("Unexpected column(s) in %s: %s\nAllowed: %s"
                     % (path, ", ".join(unknown), ", ".join(columns)))
        if missing:
            sys.exit("Missing column(s) in %s: %s" % (path, ", ".join(missing)))

        rows = []
        for line_no, raw in enumerate(reader, start=2):
            row = {}
            for col, kind in columns.items():
                row[col] = coerce(raw.get(col), kind, table, col, line_no)
            if row.get(pk) is None:
                sys.exit("%s line %d: primary key '%s' is empty."
                         % (table, line_no, pk))
            rows.append(row)
    return rows, pk


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("table", choices=sorted(SCHEMA))
    ap.add_argument("csv_path")
    ap.add_argument("--append", action="store_true",
                    help="add to the table instead of replacing its contents")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate the file without writing to Supabase")
    args = ap.parse_args()

    if not os.path.isfile(args.csv_path):
        sys.exit("No such file: %s" % args.csv_path)

    rows, pk = read_csv(args.table, args.csv_path)
    print("%s: %d rows parsed OK" % (args.table, len(rows)))
    if args.dry_run:
        print("dry run — nothing written")
        return 0
    if not rows:
        print("nothing to load")
        return 0

    url, key = load_config()
    if not args.append:
        clear(url, key, args.table, pk)

    for start in range(0, len(rows), BATCH):
        request(url, key, "POST", args.table, rows[start:start + BATCH])
        sys.stdout.write("\r  loaded %d / %d"
                         % (min(start + BATCH, len(rows)), len(rows)))
        sys.stdout.flush()
    print("\ndone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
