-- VoIP Margin Console — Supabase schema
--
-- Run this once in the Supabase SQL Editor (Dashboard > SQL Editor > New query).
-- It is idempotent: safe to re-run.
--
-- Design notes
--   * Every table is locked down with RLS. The anon key alone reads nothing;
--     a row is only visible to a signed-in (authenticated) user. That is what
--     makes it safe to host the front-end publicly on GitHub Pages.
--   * get_console_payload() returns the whole dataset as one JSON document in
--     exactly the shape the existing front-end already expects. One round trip
--     instead of ~50 paginated REST calls, and no PostgREST 1000-row cap.
--   * Column order inside the *_record builders is significant — it must match
--     the `fields` arrays the UI indexes by position. Do not reorder.

-- ---------------------------------------------------------------- tables ---

create table if not exists public.providers (
  name      text primary key,
  am        text,
  exposure  double precision,
  credit    double precision,
  terms     text,
  conf      text
);

create table if not exists public.customers (
  name      text primary key,
  am        text,
  exposure  double precision,
  credit    double precision,
  terms     text,
  conf      text
);

-- One row per destination/provider route. `id` fixes the ordering that the
-- parallel TRUNK array depends on, so never renumber it in isolation.
create table if not exists public.routes (
  id           bigint primary key,
  destination  text not null,
  provider     text not null,
  trunk        text,
  lcr          double precision,
  buy          double precision,
  sell         double precision,
  profit       double precision,
  profit_pct   double precision,
  asr          double precision,
  acd          double precision,
  calls        integer,
  dur          double precision
);

create table if not exists public.customer_routes (
  id           bigint primary key,
  customer     text not null,
  destination  text not null,
  provider     text not null,
  sell         double precision,
  buy          double precision,
  profit       double precision,
  profit_pct   double precision,
  asr          double precision,
  acd          double precision,
  calls        integer,
  dur          double precision,
  rev          double precision,
  exp          double precision
);

create table if not exists public.carriers (
  name     text primary key,
  role     text,
  am       text,
  dur      double precision,
  calls    integer,
  rev      double precision,
  profit   double precision,
  due      text,
  netbal   double precision,
  curexp   double precision,
  exp      double precision
);

-- Per-account-manager breakdown. `side` is 'c' (customer) or 'p' (provider),
-- matching the keys the UI reads off AMDATA.ams[<am>].
create table if not exists public.am_breakdown (
  id       bigint primary key,
  am       text not null,
  side     text not null check (side in ('c', 'p')),
  name     text not null,
  profit   double precision,
  calls    integer,
  dur      double precision,
  rev      double precision,
  exp      double precision,
  routes   integer,
  sec      integer
);

-- AMDATA.ams[<am>].n — total carriers touched by that AM.
create table if not exists public.am_totals (
  am              text primary key,
  total_carriers  integer
);

create table if not exists public.daily_carrier (
  id            bigint primary key,
  carrier       text not null,
  day           date not null,
  cust_rev      double precision,
  cust_profit   double precision,
  cust_dur      double precision,
  cust_calls    integer,
  prov_exp      double precision,
  prov_profit   double precision,
  prov_dur      double precision,
  prov_calls    integer
);

create index if not exists routes_destination_idx     on public.routes (destination);
create index if not exists routes_provider_idx        on public.routes (provider);
create index if not exists customer_routes_cust_idx   on public.customer_routes (customer);
create index if not exists am_breakdown_am_idx        on public.am_breakdown (am, side);
create index if not exists daily_carrier_idx          on public.daily_carrier (carrier, day);

-- ------------------------------------------------------------------- rls ---

alter table public.providers       enable row level security;
alter table public.customers       enable row level security;
alter table public.routes          enable row level security;
alter table public.customer_routes enable row level security;
alter table public.carriers        enable row level security;
alter table public.am_breakdown    enable row level security;
alter table public.am_totals       enable row level security;
alter table public.daily_carrier   enable row level security;

-- Read-only for signed-in users; writes happen exclusively through the
-- service_role key used by the import scripts, which bypasses RLS.
do $$
declare
  t text;
begin
  foreach t in array array[
    'providers', 'customers', 'routes', 'customer_routes',
    'carriers', 'am_breakdown', 'am_totals', 'daily_carrier'
  ] loop
    execute format('drop policy if exists %I on public.%I', t || '_read', t);
    execute format(
      'create policy %I on public.%I for select to authenticated using (true)',
      t || '_read', t
    );
  end loop;
end $$;

-- --------------------------------------------------------------- payload ---

-- Returns the entire console dataset in one document. SECURITY INVOKER (the
-- default) means the RLS policies above still apply, so an unauthenticated
-- caller gets empty arrays rather than data — the explicit guard below just
-- turns that into an honest error instead of a confusingly blank dashboard.
create or replace function public.get_console_payload()
returns jsonb
language plpgsql
stable
as $$
declare
  result jsonb;
begin
  if auth.role() is distinct from 'authenticated' then
    raise exception 'authentication required'
      using errcode = '42501';
  end if;

  select jsonb_build_object(

    'RAW', jsonb_build_object(
      'fields', jsonb_build_array(
        'd', 'p', 'lcr', 'buy', 'sell', 'profit',
        'profit_pct', 'asr', 'acd', 'calls', 'dur'
      ),
      'records', coalesce((
        select jsonb_agg(jsonb_build_array(
          r.destination, r.provider, r.lcr, r.buy, r.sell, r.profit,
          r.profit_pct, r.asr, r.acd, r.calls, r.dur
        ) order by r.id)
        from public.routes r
      ), '[]'::jsonb),
      'providers', coalesce((
        select jsonb_object_agg(p.name, jsonb_build_array(
          p.am, p.exposure, p.credit, p.terms, p.conf
        ))
        from public.providers p
      ), '{}'::jsonb)
    ),

    -- Index-aligned with RAW.records above: same table, same ORDER BY.
    'TRUNK', coalesce((
      select jsonb_agg(r.trunk order by r.id)
      from public.routes r
    ), '[]'::jsonb),

    'CUST', jsonb_build_object(
      'fields', jsonb_build_array(
        'c', 'd', 'p', 'sell', 'buy', 'profit', 'profit_pct',
        'asr', 'acd', 'calls', 'dur', 'rev', 'exp'
      ),
      'records', coalesce((
        select jsonb_agg(jsonb_build_array(
          cr.customer, cr.destination, cr.provider, cr.sell, cr.buy,
          cr.profit, cr.profit_pct, cr.asr, cr.acd, cr.calls,
          cr.dur, cr.rev, cr.exp
        ) order by cr.id)
        from public.customer_routes cr
      ), '[]'::jsonb),
      'customers', coalesce((
        select jsonb_object_agg(c.name, jsonb_build_array(
          c.am, c.exposure, c.credit, c.terms, c.conf
        ))
        from public.customers c
      ), '{}'::jsonb)
    ),

    'CARR', jsonb_build_object(
      'fields', jsonb_build_array(
        'name', 'role', 'am', 'dur', 'calls', 'rev',
        'profit', 'due', 'netbal', 'curexp', 'exp'
      ),
      'counts', (
        select jsonb_build_object(
          'total',      count(*),
          'asCustomer', count(*) filter (where role in ('customer', 'both')),
          'asProvider', count(*) filter (where role in ('provider', 'both')),
          'both',       count(*) filter (where role = 'both'),
          'custOnly',   count(*) filter (where role = 'customer'),
          'provOnly',   count(*) filter (where role = 'provider')
        )
        from public.carriers
      ),
      'list', coalesce((
        select jsonb_agg(jsonb_build_array(
          c.name, c.role, c.am, c.dur, c.calls, c.rev,
          c.profit, c.due, c.netbal, c.curexp, c.exp
        ) order by c.name)
        from public.carriers c
      ), '[]'::jsonb)
    ),

    'AMDATA', jsonb_build_object(
      'fields', jsonb_build_array(
        'name', 'profit', 'calls', 'dur', 'rev', 'exp', 'routes', 'sec'
      ),
      'ams', coalesce((
        select jsonb_object_agg(t.am, jsonb_build_object(
          'c', coalesce((
            select jsonb_agg(jsonb_build_array(
              b.name, b.profit, b.calls, b.dur, b.rev, b.exp, b.routes, b.sec
            ) order by b.id)
            from public.am_breakdown b
            where b.am = t.am and b.side = 'c'
          ), '[]'::jsonb),
          'p', coalesce((
            select jsonb_agg(jsonb_build_array(
              b.name, b.profit, b.calls, b.dur, b.rev, b.exp, b.routes, b.sec
            ) order by b.id)
            from public.am_breakdown b
            where b.am = t.am and b.side = 'p'
          ), '[]'::jsonb),
          'n', t.total_carriers
        ))
        from public.am_totals t
      ), '{}'::jsonb)
    ),

    'DAILY', (
      -- The UI stores a date *index* per row, so the dates array and the
      -- per-carrier rows have to be built from one shared ordering.
      with d as (
        select day, (row_number() over (order by day))::int - 1 as idx
        from (select distinct day from public.daily_carrier) u
      )
      select jsonb_build_object(
        'dates', coalesce((
          select jsonb_agg(to_char(day, 'YYYY-MM-DD') order by day) from d
        ), '[]'::jsonb),
        'byCarrier', coalesce((
          select jsonb_object_agg(x.carrier, x.rows)
          from (
            select dc.carrier,
                   jsonb_agg(jsonb_build_array(
                     d.idx, dc.cust_rev, dc.cust_profit, dc.cust_dur,
                     dc.cust_calls, dc.prov_exp, dc.prov_profit,
                     dc.prov_dur, dc.prov_calls
                   ) order by d.idx) as rows
            from public.daily_carrier dc
            join d on d.day = dc.day
            group by dc.carrier
          ) x
        ), '{}'::jsonb)
      )
    )

  ) into result;

  return result;
end $$;

revoke all on function public.get_console_payload() from public, anon;
grant execute on function public.get_console_payload() to authenticated;
