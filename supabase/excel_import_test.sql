-- Safe database staging area for testing the web Excel importer.
-- This table is intentionally NOT public.customer_routes.
-- It lets us test real browser -> Supabase writes without changing dashboard data.

create table if not exists public.customer_routes_import_test (
  batch_id      uuid not null,
  uploaded_by   uuid not null default auth.uid(),
  uploaded_at   timestamptz not null default now(),
  source_file   text not null,
  id            bigint not null,
  customer      text not null,
  destination   text not null,
  provider      text not null,
  sell          double precision,
  buy           double precision,
  profit        double precision,
  profit_pct    double precision,
  asr           double precision,
  acd           double precision,
  calls         integer,
  dur           double precision,
  rev           double precision,
  exp           double precision,
  primary key (batch_id, id)
);

create index if not exists customer_routes_import_test_user_idx
  on public.customer_routes_import_test (uploaded_by, uploaded_at desc);

create index if not exists customer_routes_import_test_batch_idx
  on public.customer_routes_import_test (batch_id);

alter table public.customer_routes_import_test enable row level security;

-- Re-running this file is safe.
drop policy if exists customer_routes_import_test_insert on public.customer_routes_import_test;
drop policy if exists customer_routes_import_test_select on public.customer_routes_import_test;
drop policy if exists customer_routes_import_test_delete on public.customer_routes_import_test;

create policy customer_routes_import_test_insert
  on public.customer_routes_import_test
  for insert to authenticated
  with check (uploaded_by = auth.uid());

create policy customer_routes_import_test_select
  on public.customer_routes_import_test
  for select to authenticated
  using (uploaded_by = auth.uid());

create policy customer_routes_import_test_delete
  on public.customer_routes_import_test
  for delete to authenticated
  using (uploaded_by = auth.uid());

revoke all on public.customer_routes_import_test from anon;
grant select, insert, delete on public.customer_routes_import_test to authenticated;
