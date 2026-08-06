"""Load the extracted JSON datasets into Supabase.

Talks to PostgREST directly with the stdlib, so there is nothing to pip install.
Requires the *service_role* key (not the anon key) because RLS makes every table
read-only for normal users by design.

    set SUPABASE_URL=https://xxxxxxxx.supabase.co
    set SUPABASE_SERVICE_KEY=eyJhbGci...
    python scripts\\seed_supabase.py

Each run replaces the contents of the tables it touches. Run schema.sql first.
"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")

BATCH = 1000


def load_config():
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()

    # Fall back to supabase/.env so the keys can live in one gitignored file.
    env_path = os.path.join(ROOT, "supabase", ".env")
    if (not url or not key) and os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if k.strip() == "SUPABASE_URL" and not url:
                    url = v.rstrip("/")
                elif k.strip() == "SUPABASE_SERVICE_KEY" and not key:
                    key = v

    if not url or not key:
        sys.exit(
            "Missing config. Set SUPABASE_URL and SUPABASE_SERVICE_KEY as\n"
            "environment variables, or create supabase/.env with those keys."
        )
    return url, key


def request(url, key, method, path, body=None, extra_headers=None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url + "/rest/v1/" + path, data=data, method=method)
    req.add_header("apikey", key)
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=minimal")
    for hk, hv in (extra_headers or {}).items():
        req.add_header(hk, hv)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:600]
        sys.exit("\n%s %s failed (HTTP %s):\n%s" % (method, path, err.code, detail))
    except urllib.error.URLError as err:
        sys.exit("\nCould not reach %s: %s" % (url, err.reason))


def clear(url, key, table, pk):
    # PostgREST refuses an unfiltered DELETE, so use a predicate that is always
    # true rather than enumerating keys.
    if pk == "id":
        request(url, key, "DELETE", "%s?id=gte.0" % table)
    else:
        request(url, key, "DELETE", "%s?%s=neq.%%00" % (table, pk))


def push(url, key, table, rows, pk):
    clear(url, key, table, pk)
    total = len(rows)
    for start in range(0, total, BATCH):
        chunk = rows[start:start + BATCH]
        request(url, key, "POST", table, chunk)
        done = min(start + BATCH, total)
        sys.stdout.write("\r  %-16s %6d / %d" % (table, done, total))
        sys.stdout.flush()
    if total == 0:
        sys.stdout.write("\r  %-16s %6d / %d" % (table, 0, 0))
    sys.stdout.write("\n")


def read(name):
    with open(os.path.join(DATA_DIR, name + ".json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def party_rows(mapping):
    """providers / customers share the [am, exposure, credit, terms, conf] shape."""
    out = []
    for name, v in mapping.items():
        v = (list(v) + [None] * 5)[:5]
        out.append({
            "name": name, "am": v[0], "exposure": v[1],
            "credit": v[2], "terms": v[3], "conf": v[4],
        })
    return out


def build():
    raw = read("raw")
    trunk = read("trunk")
    cust = read("cust")
    amdata = read("amdata")
    carr = read("carr")
    daily = read("daily")

    if len(trunk) != len(raw["records"]):
        sys.exit(
            "TRUNK (%d) and RAW.records (%d) lengths differ — the arrays are "
            "positionally paired, so this must be fixed before loading."
            % (len(trunk), len(raw["records"]))
        )

    routes = []
    for i, r in enumerate(raw["records"]):
        routes.append({
            "id": i, "destination": r[0], "provider": r[1], "trunk": trunk[i],
            "lcr": r[2], "buy": r[3], "sell": r[4], "profit": r[5],
            "profit_pct": r[6], "asr": r[7], "acd": r[8],
            "calls": r[9], "dur": r[10],
        })

    customer_routes = []
    for i, r in enumerate(cust["records"]):
        customer_routes.append({
            "id": i, "customer": r[0], "destination": r[1], "provider": r[2],
            "sell": r[3], "buy": r[4], "profit": r[5], "profit_pct": r[6],
            "asr": r[7], "acd": r[8], "calls": r[9], "dur": r[10],
            "rev": r[11], "exp": r[12],
        })

    carriers = []
    for r in carr["list"]:
        carriers.append({
            "name": r[0], "role": r[1], "am": r[2], "dur": r[3], "calls": r[4],
            "rev": r[5], "profit": r[6], "due": r[7], "netbal": r[8],
            "curexp": r[9], "exp": r[10],
        })

    am_breakdown, am_totals, bid = [], [], 0
    for am, blocks in amdata["ams"].items():
        for side in ("c", "p"):
            for r in blocks.get(side, []):
                am_breakdown.append({
                    "id": bid, "am": am, "side": side, "name": r[0],
                    "profit": r[1], "calls": r[2], "dur": r[3], "rev": r[4],
                    "exp": r[5], "routes": r[6], "sec": r[7],
                })
                bid += 1
        am_totals.append({"am": am, "total_carriers": blocks.get("n")})

    dates = daily["dates"]
    daily_rows, did = [], 0
    for carrier, entries in daily["byCarrier"].items():
        for e in entries:
            daily_rows.append({
                "id": did, "carrier": carrier, "day": dates[e[0]],
                "cust_rev": e[1], "cust_profit": e[2], "cust_dur": e[3],
                "cust_calls": e[4], "prov_exp": e[5], "prov_profit": e[6],
                "prov_dur": e[7], "prov_calls": e[8],
            })
            did += 1

    return [
        ("providers",       party_rows(raw["providers"]),   "name"),
        ("customers",       party_rows(cust["customers"]),  "name"),
        ("carriers",        carriers,                       "name"),
        ("am_totals",       am_totals,                      "am"),
        ("am_breakdown",    am_breakdown,                   "id"),
        ("routes",          routes,                         "id"),
        ("customer_routes", customer_routes,                "id"),
        ("daily_carrier",   daily_rows,                     "id"),
    ]


def main():
    url, key = load_config()
    tables = build()
    print("Seeding %s\n" % url)
    for table, rows, pk in tables:
        push(url, key, table, rows, pk)
    print("\nDone. %d rows total." % sum(len(r) for _, r, _ in tables))
    return 0


if __name__ == "__main__":
    sys.exit(main())
