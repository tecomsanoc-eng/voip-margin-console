"""Turn the weekly billing exports into CSVs for scripts/import_csv.py.

    python scripts/build_weekly.py exports/ out/

Files are detected by their header columns, not filenames.
"""
import csv, os, re, sys
from collections import Counter, defaultdict
import pandas as pd

LEGAL_SUFFIXES = {'ltd', 'limited', 'llc', 'pte', 'srl', 'inc', 'sal', 'offshore', 'co'}
MARKERS = {'tec', 'com', 'loc'}


def raw_name(value):
    return value.strip() if isinstance(value, str) else ''


def tokens(value):
    # Dotted legal abbreviations (S.A.L, L.L.C, etc.) are suffixes too.
    value = raw_name(value).lower()
    value = re.sub(r"\b(?:[a-z]\.){2,}[a-z]?", lambda m: m[0].replace('.', ''), value)
    return tuple(w for w in re.findall(r'[a-z0-9]+', value) if w not in LEGAL_SUFFIXES)


def norm(value):
    return ' '.join(tokens(value))


class CarrierResolver:
    """Roster identities never pass through traffic normalization or fuzzy matching."""

    def __init__(self, details=None, exposure=None):
        self.names, self.by_name, self.examined = {}, {}, {}
        self.sources = defaultdict(set)
        for frame, column in ((exposure, 'Carrier'), (details, 'Carrier Name')):
            if frame is None:
                continue
            seen = set()
            for _, row in frame.drop_duplicates().iterrows():
                name = raw_name(row.get(column))
                if not name:
                    raise ValueError('Authoritative roster record has no carrier name')
                if name in seen:
                    raise ValueError('Duplicate authoritative carrier name: ' + name)
                seen.add(name)
                if name in self.by_name:
                    continue  # Exact name join between snapshots only.
                carrier_id = row.get('Carrier Id') if column == 'Carrier' else None
                identity = ('exposure:' + str(carrier_id).strip()
                            if pd.notna(carrier_id) and str(carrier_id).strip()
                            else 'roster:' + name)
                if identity in self.names:
                    raise ValueError('Authoritative roster records collapse: ' + identity)
                self.by_name[name] = identity
                self.names[identity] = name
        self.normalized, self.marked, self.compact = (defaultdict(set) for _ in range(3))
        for identity, name in self.names.items():
            self.normalized[norm(name)].add(identity)
            markers, base = self.signature(name)
            self.marked[(markers, base)].add(identity)
            self.compact[(markers, ''.join(base))].add(identity)

    @staticmethod
    def signature(name):
        words = tokens(name)
        return (tuple(sorted(w for w in words if w in MARKERS)),
                tuple(w for w in words if w not in MARKERS))

    def roster_key(self, name):
        return self.by_name[raw_name(name)]

    def resolve(self, name):
        name = raw_name(name)
        if name in self.by_name:
            return self.by_name[name], ()
        markers, base = self.signature(name)
        compact = ''.join(base)
        # All equivalent formats compete together: a unique normalized string
        # must not hide another roster name with reordered markers or spacing.
        equivalent = (self.normalized.get(norm(name), set()) |
                      self.marked.get((markers, base), set()) |
                      self.compact.get((markers, compact), set()))
        if equivalent:
            return self.choose(equivalent)
        candidates, supported, marker_conflicts = set(), set(), set()
        for identity, roster_name in self.names.items():
            other_markers, other_base = self.signature(roster_name)
            other = ''.join(other_base)
            if not compact or not other:
                continue
            if markers != other_markers:
                if compact == other or (min(len(compact), len(other)) >= 3 and
                                        (compact.startswith(other) or other.startswith(compact))):
                    marker_conflicts.add(identity)
                continue
            # Spacing inside a name is equivalent, but markers remain separate.
            if compact == other:
                candidates.add(identity)
                supported.add(identity)
                continue
            if min(len(compact), len(other)) < 3:
                continue
            if not (compact.startswith(other) or other.startswith(compact)):
                continue
            # Keep every plausible prefix competitor, even if only one meets
            # the stronger acceptance rule below. Never rank away ambiguity.
            candidates.add(identity)
            if min(len(compact), len(other)) < 6:
                continue
            # A marked traffic name may omit trailing roster words only at a
            # whole-word boundary. All those words remain in the roster index;
            # e.g. Stream matches both Stream Telecom and Stream-iT, not one.
            whole_prefix = bool(markers) and any(
                compact == ''.join(other_base[:end])
                for end in range(1, len(other_base)))
            near_prefix = (len(base) == len(other_base) and
                           min(len(compact), len(other)) / max(len(compact), len(other)) >= .85)
            if whole_prefix or near_prefix:
                supported.add(identity)
        if supported:
            return self.choose(candidates)
        # Plausible but insufficient evidence is not a genuinely unknown name.
        return None, tuple(sorted(self.names[k] for k in candidates | marker_conflicts))

    def choose(self, candidates):
        if len(candidates) == 1:
            return next(iter(candidates)), ()
        return None, tuple(sorted(self.names[k] for k in candidates))

    def traffic_key(self, name, source=None):
        name = raw_name(name)
        if not name:
            return ''
        if source is not None:
            self.sources[name].add(source)
        if name not in self.examined:
            self.examined[name] = self.resolve(name)
        identity, _ = self.examined[name]
        # Unresolved traffic stays separate, including ambiguous aliases.
        return identity or 'traffic:' + name

    def validate(self, identities, carriers):
        if not set(self.names) <= set(identities):
            raise ValueError('Authoritative roster records collapse or are missing')
        counts = Counter(row['name'] for row in carriers)
        if any(counts[name] != 1 for name in self.names.values()):
            raise ValueError('Duplicate or missing authoritative carrier names')
        if len(carriers) < len(self.names):
            raise ValueError('Output carrier count below authoritative roster count')

    def diagnostics(self, output_count):
        matched = sum(identity is not None for identity, _ in self.examined.values())
        print('Authoritative roster: %d carriers' % len(self.names))
        print('Traffic aliases examined: %d' % len(self.examined))
        print('Traffic aliases matched: %d' % matched)
        print('Traffic aliases unresolved: %d' % (len(self.examined) - matched))
        unresolved = {name for name, (identity, _) in self.examined.items() if identity is None}
        transactional = {name for name in unresolved if self.sources[name] & {'Gross', 'Full'}}
        print('Gross/Full unresolved: %d' % len(transactional))
        print('LCR-only unresolved: %d' % sum(self.sources[name] == {'LCR'} for name in unresolved))
        print('Output carriers: %d' % output_count)
        for name, (identity, candidates) in sorted(self.examined.items()):
            if identity is None:
                sources = ','.join(source for source in ('Gross', 'Full', 'LCR')
                                   if source in self.sources[name])
                print('  unresolved [%s]: %s%s' % (
                    sources, name, ' | candidates: ' + '; '.join(candidates) if candidates else ''))


def num(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ''
    if isinstance(v, str):
        v = v.replace(',', '').replace('%', '').strip()
        if not v:
            return ''
    try:
        return float(v)
    except (TypeError, ValueError):
        return ''


def read_any(path):
    if path.lower().endswith('.csv'):
        with open(path, encoding='utf-8-sig', errors='replace') as fh:
            line = fh.readline()
        return pd.read_csv(path, sep=';' if line.count(';') > line.count(',') else ',',
                           dtype=object)
    return pd.read_excel(path, dtype=object)


def classify(cols):
    c = {str(x).strip().lower() for x in cols}
    if {'revenue', 'expense', 'profit'} <= c:
        return 'gross'
    if 'destination' in c and ('ig asr (%)' in c or 'acd (min)' in c):
        return 'full'
    if 'carrier name' in c and 'carrier account manager' in c:
        return 'details'
    if 'carrier' in c and 'current exposure' in c:
        return 'exposure'
    return None


def load_lcr(path):
    """Wide sheet: header on row 2, then repeating Provider-Epg/Volume/Rate."""
    raw = pd.read_excel(path, header=None, dtype=object)
    if len(raw) < 3 or 'Destination' not in [str(x).strip() for x in raw.iloc[1]]:
        return None
    out = []
    for _, row in raw.iloc[2:].iterrows():
        v = list(row)
        if not isinstance(v[0], str) or not v[0].strip():
            continue
        for i in range(2, len(v) - 2, 3):
            pe = v[i]
            if not isinstance(pe, str) or not pe.strip():
                continue
            # Provider names contain hyphens (AAA-TEL-Tec-AAA_S_B_T), so the
            # EPGroup is what follows the LAST hyphen, never the first.
            prov, _, epg = pe.rpartition('-')
            out.append((v[0].strip(), prov.strip(), epg.strip(),
                        num(v[i + 1]), num(v[i + 2])))
    return pd.DataFrame(out, columns=['dest', 'provider', 'trunk', 'vol', 'rate'])


def main(indir, outdir):
    os.makedirs(outdir, exist_ok=True)

    # Two kinds of input:
    #   transactional  - Gross Profit, Full info. One file per week. These
    #                    ACCUMULATE: every week ever exported is read, so the
    #                    console keeps full history and the date filter works.
    #   snapshot       - LCR, Exposure, Carrier Details. These describe the
    #                    current state, not a period. Only the newest is used;
    #                    older copies would resurrect stale rates and limits.
    gross_parts, full_parts = [], []
    snapshots, lcr_file = {}, None

    files = []
    for root, _dirs, names in os.walk(indir):
        for n in sorted(names):
            if n.lower().endswith(('.xlsx', '.xls', '.csv')):
                files.append(os.path.join(root, n))
    files.sort(key=lambda p: (os.path.getmtime(p), p))

    for path in files:
        rel = os.path.relpath(path, indir)
        try:
            df = read_any(path)
        except Exception as exc:
            print('  skip %-44s (%s)' % (rel, exc)); continue
        kind = classify(df.columns)
        if kind == 'gross':
            gross_parts.append(df); print('  %-9s %-44s %d rows' % (kind, rel, len(df)))
        elif kind == 'full':
            full_parts.append(df);  print('  %-9s %-44s %d rows' % (kind, rel, len(df)))
        elif kind:
            snapshots[kind] = df;   print('  %-9s %-44s %d rows (snapshot)' % (kind, rel, len(df)))
        else:
            got = load_lcr(path)
            if got is not None and len(got):
                lcr_file = got
                print('  %-9s %-44s %d pairs (snapshot)' % ('lcr', rel, len(got)))

    found = dict(snapshots)
    if gross_parts:
        found['gross'] = pd.concat(gross_parts, ignore_index=True)
    if full_parts:
        found['full'] = pd.concat(full_parts, ignore_index=True)
    lcr = lcr_file

    if 'gross' not in found:
        sys.exit('Gross Profit export not found.')

    g = found['gross'].rename(columns=lambda x: str(x).strip())
    # The billing system appends a grand-total row: no Date, no Customer, and
    # every figure equal to the file's sum. Left in it doubles the dashboard.
    # Filter on Date, NOT Provider - 100 real zero-traffic rows have no
    # Provider but are legitimate.
    before = len(g)
    g = g[g['Date'].notna() & g['Customer'].notna()]
    if len(g) != before:
        print('  dropped %d grand-total row(s)' % (before - len(g)))

    # Re-exporting a week under a new filename would otherwise double it.
    before = len(g)
    g = g.drop_duplicates()
    if len(g) != before:
        print('  dropped %d duplicate row(s) - the same week appeared twice'
              % (before - len(g)))
    try:
        print('  covering %s to %s (%d days)'
              % (pd.to_datetime(g['Date']).min().date(),
                 pd.to_datetime(g['Date']).max().date(),
                 pd.to_datetime(g['Date']).dt.date.nunique()))
    except Exception:
        pass

    full, expo, det = found.get('full'), found.get('exposure'), found.get('details')
    if full is not None:
        full = full.rename(columns=lambda x: str(x).strip())
        full = full[full['Customer'].notna()].drop_duplicates()

    if expo is not None:
        expo = expo.rename(columns=lambda x: str(x).strip()).drop_duplicates()
    if det is not None:
        det = det.rename(columns=lambda x: str(x).strip()).drop_duplicates()
    resolver = CarrierResolver(det, expo)
    key = resolver.traffic_key
    display = dict(resolver.names)
    active_unknowns = set()
    # Examine all aliases for diagnostics, but a rate-sheet entry or zero-only
    # placeholder is not evidence of a new carrier. Ambiguous names stay out
    # of the carrier roster while retaining their raw labels in traffic CSVs.
    for source, frame in (('Gross', g), ('Full', full), ('LCR', lcr)):
        if frame is None:
            continue
        columns = ('provider',) if source == 'LCR' else ('Customer', 'Provider')
        metrics = [c for c in frame.columns if c in ('Revenue', 'Expense', 'Profit')
                   or str(c).lower().startswith('duration') or 'call' in str(c).lower()]
        for _, row in frame.iterrows():
            active = source != 'LCR' and any((num(row.get(c)) or 0) != 0 for c in metrics)
            for column in columns:
                value = raw_name(row.get(column))
                if not value:
                    continue
                identity = resolver.traffic_key(value, source)
                display.setdefault(identity, value)
                resolved, candidates = resolver.examined[value]
                if active and resolved is None and not candidates:
                    active_unknowns.add(identity)

    # Carrier Details holds usernames (m.zreik); Exposure holds display names
    # (Mostafa zreik). Join the two on carrier identity to derive the map.
    user2name = {}
    if det is not None and expo is not None:
        emap = {resolver.roster_key(r['Carrier']): r.get('Account Manager') for _, r in expo.iterrows()}
        votes = Counter()
        for _, r in det.iterrows():
            us, ds = r.get('Carrier Account Manager'), emap.get(resolver.roster_key(r['Carrier Name']))
            if isinstance(us, str) and isinstance(ds, str):
                us, ds = [x.strip() for x in us.split(',')], [x.strip() for x in ds.split(',')]
                if len(us) == 1 and len(ds) == 1:
                    votes[(us[0], ds[0])] += 1
        for (u, d), _ in votes.most_common():
            user2name.setdefault(u, d)

    am_of, ctype, credit_c, credit_p = {}, {}, {}, {}
    if det is not None:
        for _, r in det.iterrows():
            k = resolver.roster_key(r['Carrier Name'])
            u = r.get('Carrier Account Manager')
            if isinstance(u, str) and u.strip():
                names = [user2name.get(x.strip(), x.strip()) for x in u.split(',')]
                am_of[k] = '; '.join(dict.fromkeys(names))
            # Carrier Type is the contractual relationship and covers the roster of
            # carriers. Traffic only tells you who was active in this one week.
            t = r.get('Carrier Type')
            if isinstance(t, str) and t.strip():
                ctype[k] = t.strip().lower()
            cc, cp = num(r.get('Credit Limit as Customer')), num(r.get('Credit Limit as Provider'))
            if cc != '':
                credit_c[k] = cc
            if cp != '':
                credit_p[k] = cp
    exposure = {}
    if expo is not None:
        for _, r in expo.iterrows():
            k = resolver.roster_key(r['Carrier'])
            if k not in am_of and isinstance(r.get('Account Manager'), str):
                am_of[k] = r['Account Manager'].strip()
            exposure[k] = (num(r.get('Current Exposure')),
                           num(r.get('Credit Limit (Customer)')),
                           r.get('Payment Terms (Customer)') or '')

    qos, dests_for, trunk_full, trunk_lcr = {}, defaultdict(set), {}, {}
    if full is not None:
        dcol = next((c for c in full.columns if c.lower().startswith('duration')), None)
        for _, r in full.iterrows():
            d = r.get('Destination')
            if not isinstance(d, str) or not d.strip():
                continue
            d, ck, pk = d.strip(), key(r['Customer']), key(r['Provider'])
            qos[(ck, pk, d)] = (num(r.get('IG ASR (%)')), num(r.get('ACD (min)')),
                                num(r.get('Successful Calls')), num(r.get(dcol)) or 0)
            dests_for[(ck, pk)].add(d)
            if isinstance(r.get('Prov. Epgroup'), str):
                trunk_full.setdefault((pk, d), r['Prov. Epgroup'])

    lcr_rate = {}
    if lcr is not None:
        for _, r in lcr.iterrows():
            k, v = (key(r['provider']), r['dest']), r['rate']
            trunk_lcr.setdefault(k, r['trunk'])
            if v != '' and v > 0 and (k not in lcr_rate or v < lcr_rate[k]):
                lcr_rate[k] = v

    # LCR is authoritative for the trunk; Full info only fills the gaps.
    trunk_of = dict(trunk_full); trunk_of.update(trunk_lcr)

    # If the export carries Sell Destination, money is attributed directly and
    # aggregated per customer+destination+provider. Older exports without that
    # column fall back to splitting each row across the destinations Full info
    # shows for the pair, weighted by minutes.
    has_dest = 'Sell Destination' in g.columns
    calls_col = next((c for c in ('Succ. Callcount', 'Successful Calls', 'Succ. Calls')
                      if c in g.columns), None)
    if has_dest:
        print('  gross export carries Sell Destination - attributing directly')

    bucket = defaultdict(lambda: dict(dur=0.0, rev=0.0, exp=0.0, profit=0.0, calls=0.0))
    for _, r in g.iterrows():
        ck, pk = key(r.get('Customer')), key(r.get('Provider'))
        if not pk:
            continue          # zero-traffic placeholder, no provider to route to
        dur, rev = num(r.get('Duration (m)')) or 0, num(r.get('Revenue')) or 0
        exp, prof = num(r.get('Expense')) or 0, num(r.get('Profit')) or 0
        cls = (num(r.get(calls_col)) or 0) if calls_col else 0

        if has_dest:
            d = r.get('Sell Destination')
            d = d.strip() if isinstance(d, str) and d.strip() else '(unspecified)'
            parts = [(d, 1.0)]
        else:
            ds = sorted(dests_for.get((ck, pk), []))
            if not ds:
                parts = [('(unspecified)', 1.0)]
            else:
                mins = [qos.get((ck, pk, x), (0, 0, 0, 0))[3] or 0 for x in ds]
                tot = sum(mins)
                w = [m / tot for m in mins] if tot else [1 / len(ds)] * len(ds)
                parts = list(zip(ds, w))

        for d, wt in parts:
            b = bucket[(ck, pk, d)]
            b['dur'] += dur * wt; b['rev'] += rev * wt
            b['exp'] += exp * wt; b['profit'] += prof * wt
            b['calls'] += cls * wt

    rows, cid = [], 0
    for (ck, pk, d), b in sorted(bucket.items(), key=lambda kv: (str(kv[0][2]), str(kv[0][0]), str(kv[0][1]))):
        asr, acd, fcalls, _ = qos.get((ck, pk, d), ('', '', '', 0))
        sd, sr, se, sp = b['dur'], b['rev'], b['exp'], b['profit']
        cid += 1
        rows.append(dict(id=cid, customer=display.get(ck, ck), destination=d,
                         provider=display.get(pk, pk),
                         sell=round(sr / sd, 6) if sd else '',
                         buy=round(se / sd, 6) if sd else '',
                         profit=round(sp, 6),
                         profit_pct=round(100 * sp / sr, 4) if sr else '',
                         asr=asr, acd=acd,
                         calls=int(round(b['calls'])) if calls_col else (fcalls or 0),
                         dur=round(sd, 4), rev=round(sr, 6), exp=round(se, 6)))

    agg = defaultdict(lambda: dict(dur=0.0, rev=0.0, exp=0.0, profit=0.0, calls=0.0,
                                   asr=[], acd=[]))
    for r in rows:
        a = agg[(r['destination'], r['provider'])]
        for f in ('dur', 'rev', 'exp', 'profit', 'calls'):
            a[f] += r[f] or 0
        for f in ('asr', 'acd'):
            if r[f] != '':
                a[f].append(r[f])

    identity_by_display = {name: identity for identity, name in display.items()}
    routes = []
    for i, ((dest, prov), a) in enumerate(sorted(agg.items(),
                                                 key=lambda kv: (str(kv[0][0]), str(kv[0][1])))):
        pk = identity_by_display[prov]
        # id must stay contiguous from 0: TRUNK is a positional array.
        routes.append(dict(id=i, destination=dest, provider=prov,
                           trunk=trunk_of.get((pk, dest), prov),
                           lcr=lcr_rate.get((pk, dest), ''),
                           buy=round(a['exp'] / a['dur'], 6) if a['dur'] else '',
                           sell=round(a['rev'] / a['dur'], 6) if a['dur'] else '',
                           profit=round(a['profit'], 6),
                           profit_pct=round(100 * a['profit'] / a['rev'], 4) if a['rev'] else '',
                           asr=round(sum(a['asr']) / len(a['asr']), 4) if a['asr'] else '',
                           acd=round(sum(a['acd']) / len(a['acd']), 4) if a['acd'] else '',
                           calls=int(a['calls']), dur=round(a['dur'], 4)))

    side = defaultdict(lambda: dict(cust=dict(rev=0.0, profit=0.0, dur=0.0, calls=0.0),
                                    prov=dict(exp=0.0, profit=0.0, dur=0.0, calls=0.0)))
    daily_map = defaultdict(lambda: dict(cust_rev=0.0, cust_profit=0.0, cust_dur=0.0,
                                         cust_calls=0.0, prov_exp=0.0, prov_profit=0.0,
                                         prov_dur=0.0, prov_calls=0.0))
    for _, r in g.iterrows():
        ck, pk = key(r.get('Customer')), key(r.get('Provider'))
        dur, rev = num(r.get('Duration (m)')) or 0, num(r.get('Revenue')) or 0
        exp, prof = num(r.get('Expense')) or 0, num(r.get('Profit')) or 0
        day = str(r.get('Date'))[:10]
        cls = (num(r.get(calls_col)) or 0) if calls_col else 0
        if ck:
            s = side[ck]['cust']
            s['rev'] += rev; s['profit'] += prof; s['dur'] += dur; s['calls'] += cls
            d = daily_map[(ck, day)]
            d['cust_rev'] += rev; d['cust_profit'] += prof
            d['cust_dur'] += dur; d['cust_calls'] += cls
        if pk:
            s = side[pk]['prov']
            s['exp'] += exp; s['profit'] += prof; s['dur'] += dur; s['calls'] += cls
            d = daily_map[(pk, day)]
            d['prov_exp'] += exp; d['prov_profit'] += prof
            d['prov_dur'] += dur; d['prov_calls'] += cls

    is_c = {key(x) for x in g['Customer'].dropna() if key(x)}
    is_p = {key(x) for x in g['Provider'].dropna() if key(x)}
    every = set(resolver.names) | active_unknowns

    carriers = []
    for k in sorted(every):
        s = side.get(k, {'cust': {}, 'prov': {}})
        cexp, credit, terms = exposure.get(k, ('', '', ''))
        carriers.append(dict(
            name=display.get(k, k),
            # get_console_payload() filters on lowercase 'customer' / 'provider'
            # / 'both'. Capitalised values match nothing and every role tile
            # on the dashboard reads zero.
            # Contractual role where the roster knows it; otherwise infer from
            # this week's traffic. The dashboard shows activity separately in
            # its own active/idle tile, so role should mean the relationship,
            # not whether they happened to send calls in these seven days.
            role=ctype.get(k) or ('both' if k in is_c and k in is_p else
                                  'customer' if k in is_c else
                                  'provider' if k in is_p else 'idle'),
            am=am_of.get(k, 'Unassigned'),
            dur=round(s['cust'].get('dur', 0) + s['prov'].get('dur', 0), 4),
            calls=int(round(s['cust'].get('calls', 0) + s['prov'].get('calls', 0))),
            rev=round(s['cust'].get('rev', 0), 6),
            profit=round(s['cust'].get('profit', 0) + s['prov'].get('profit', 0), 6),
            due='', netbal='', curexp=cexp, exp=round(s['prov'].get('exp', 0), 6)))

    breakdown, bid = [], 0
    for k in sorted(every):
        s = side.get(k)
        if not s:
            continue
        # schema.sql constrains side to 'c'/'p'; 'Customer' fails the check.
        for tag, d in (('c', s['cust']), ('p', s['prov'])):
            if not d.get('dur') and not d.get('rev') and not d.get('exp'):
                continue
            bid += 1
            breakdown.append(dict(id=bid, am=am_of.get(k, 'Unassigned'), side=tag,
                                  name=display.get(k, k), profit=round(d.get('profit', 0), 6),
                                  calls=int(round(d.get('calls', 0))),
                                  dur=round(d.get('dur', 0), 4),
                                  rev=round(d.get('rev', 0), 6),
                                  exp=round(d.get('exp', 0), 6), routes=0, sec=0))

    totals = [dict(am=a, total_carriers=n) for a, n in
              sorted(Counter(am_of.get(k, 'Unassigned') for k in every).items())]

    daily = [dict(id=i, carrier=display.get(k, k), day=day,
                  cust_rev=round(d['cust_rev'], 6), cust_profit=round(d['cust_profit'], 6),
                  cust_dur=round(d['cust_dur'], 4),
                  cust_calls=int(round(d['cust_calls'])),
                  prov_exp=round(d['prov_exp'], 6), prov_profit=round(d['prov_profit'], 6),
                  prov_dur=round(d['prov_dur'], 4),
                  prov_calls=int(round(d['prov_calls'])))
             for i, ((k, day), d) in enumerate(
                 sorted(daily_map.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))))]

    def side_table(members, credit_map):
        out = []
        for k in sorted(members):
            cexp, credit, terms = exposure.get(k, ('', '', ''))
            out.append(dict(name=display.get(k, k), am=am_of.get(k, 'Unassigned'),
                            exposure=cexp,
                            credit=credit_map.get(k, credit),
                            terms=terms, conf=''))
        return out

    def write(name, data, cols):
        with open(os.path.join(outdir, name + '.csv'), 'w', newline='',
                  encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
            w.writeheader(); w.writerows(data)
        print('  %-20s %6d rows' % (name + '.csv', len(data)))

    resolver.validate(every, carriers)
    resolver.diagnostics(len(carriers))

    print('\nwriting:')
    write('routes', routes, ['id','destination','provider','trunk','lcr','buy','sell',
                             'profit','profit_pct','asr','acd','calls','dur'])
    write('customer_routes', rows, ['id','customer','destination','provider','sell','buy',
                                    'profit','profit_pct','asr','acd','calls','dur','rev','exp'])
    write('carriers', carriers, ['name','role','am','dur','calls','rev','profit','due',
                                 'netbal','curexp','exp'])
    write('providers', side_table(is_p, credit_p), ['name','am','exposure','credit','terms','conf'])
    write('customers', side_table(is_c, credit_c), ['name','am','exposure','credit','terms','conf'])
    write('am_breakdown', breakdown, ['id','am','side','name','profit','calls','dur','rev',
                                      'exp','routes','sec'])
    write('am_totals', totals, ['am','total_carriers'])
    write('daily_carrier', daily, ['id','carrier','day','cust_rev','cust_profit','cust_dur',
                                   'cust_calls','prov_exp','prov_profit','prov_dur','prov_calls'])
    print('\nrevenue %.4f   AM names resolved %d   unassigned carriers %d'
          % (sum(r['rev'] for r in rows), len(user2name),
             sum(1 for c in carriers if c['am'] == 'Unassigned')))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
