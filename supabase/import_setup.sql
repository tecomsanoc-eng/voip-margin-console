-- VoIP Margin Console — browser Excel import setup
-- Run this ONCE in Supabase SQL Editor.
-- No service_role key is required in the browser.
--
-- Creates:
--   1) customer_routes_import_test  - safe staging table for browser tests
--   2) import_batches               - audit log
--   3) import_customer_routes()    - protected production import RPC
--
-- Production import is UPSERT-only: existing IDs are updated and new IDs are inserted.
-- Nothing is deleted.

begin;

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

create table if not exists public.import_batches (
  batch_id       uuid primary key,
  uploaded_by    uuid not null,
  uploaded_at    timestamptz not null default now(),
  source_file    text not null,
  table_name     text not null,
  row_count      integer not null,
  status         text not null check (status in ('success','failed')),
  error_message  text
);

create index if not exists import_batches_user_idx
  on public.import_batches (uploaded_by, uploaded_at desc);

alter table public.import_batches enable row level security;

drop policy if exists import_batches_select on public.import_batches;
create policy import_batches_select
  on public.import_batches
  for select to authenticated
  using (uploaded_by = auth.uid());

revoke all on public.import_batches from anon;
grant select on public.import_batches to authenticated;

create or replace function public.import_customer_routes(
  p_rows jsonb,
  p_source_file text default 'browser-import.xlsx'
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_uid uuid := auth.uid();
  v_batch uuid := gen_random_uuid();
  v_count integer;
  v_file text := left(coalesce(nullif(trim(p_source_file), ''), 'browser-import.xlsx'), 255);
begin
  if v_uid is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;

  if jsonb_typeof(p_rows) <> 'array' then
    raise exception 'p_rows must be a JSON array';
  end if;

  v_count := jsonb_array_length(p_rows);

  if v_count < 1 then
    raise exception 'No rows supplied';
  end if;

  if v_count > 20000 then
    raise exception 'Maximum 20000 rows per import';
  end if;

  insert into public.import_batches
    (batch_id, uploaded_by, source_file, table_name, row_count, status)
  values
    (v_batch, v_uid, v_file, 'customer_routes', v_count, 'success');

  insert into public.customer_routes (
    id, customer, destination, provider, sell, buy, profit,
    profit_pct, asr, acd, calls, dur, rev, exp
  )
  select
    x.id,
    nullif(trim(x.customer), ''),
    nullif(trim(x.destination), ''),
    nullif(trim(x.provider), ''),
    x.sell, x.buy, x.profit, x.profit_pct, x.asr, x.acd,
    x.calls, x.dur, x.rev, x.exp
  from jsonb_to_recordset(p_rows) as x(
    id bigint,
    customer text,
    destination text,
    provider text,
    sell double precision,
    buy double precision,
    profit double precision,
    profit_pct double precision,
    asr double precision,
    acd double precision,
    calls integer,
    dur double precision,
    rev double precision,
    exp double precision
  )
  where x.id is not null
    and nullif(trim(x.customer), '') is not null
    and nullif(trim(x.destination), '') is not null
    and nullif(trim(x.provider), '') is not null
  on conflict (id) do update set
    customer    = excluded.customer,
    destination = excluded.destination,
    provider    = excluded.provider,
    sell        = excluded.sell,
    buy         = excluded.buy,
    profit      = excluded.profit,
    profit_pct  = excluded.profit_pct,
    asr         = excluded.asr,
    acd         = excluded.acd,
    calls       = excluded.calls,
    dur         = excluded.dur,
    rev         = excluded.rev,
    exp         = excluded.exp;

  return jsonb_build_object(
    'success', true,
    'batch_id', v_batch,
    'rows_received', v_count,
    'source_file', v_file,
    'table', 'customer_routes'
  );
exception when others then
  if v_uid is not null then
    insert into public.import_batches
      (batch_id, uploaded_by, source_file, table_name, row_count, status, error_message)
    values
      (v_batch, v_uid, v_file, 'customer_routes', coalesce(v_count,0), 'failed', sqlerrm)
    on conflict (batch_id) do update set status='failed', error_message=excluded.error_message;
  end if;
  raise;
end;
$$;

revoke all on function public.import_customer_routes(jsonb, text) from public, anon;
grant execute on function public.import_customer_routes(jsonb, text) to authenticated;

commit;
