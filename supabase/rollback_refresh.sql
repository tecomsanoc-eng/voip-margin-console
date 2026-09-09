-- OWNER-EXECUTED ONLY. Run the entire file on one connection as postgres.
-- Any error aborts the transaction. With psql use -X -v ON_ERROR_STOP=1.
-- Stop staging loaders and other refresh jobs until promotion completes.
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '5min';

LOCK TABLE public.providers, public.customers, public.carriers, public.routes, public.customer_routes, public.am_breakdown, public.am_totals, public.daily_carrier IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE refresh_backup_20260909.providers, refresh_backup_20260909.customers, refresh_backup_20260909.carriers, refresh_backup_20260909.routes, refresh_backup_20260909.customer_routes, refresh_backup_20260909.am_breakdown, refresh_backup_20260909.am_totals, refresh_backup_20260909.daily_carrier IN SHARE MODE;
DELETE FROM public.daily_carrier;
DELETE FROM public.am_totals;
DELETE FROM public.am_breakdown;
DELETE FROM public.customer_routes;
DELETE FROM public.routes;
DELETE FROM public.carriers;
DELETE FROM public.customers;
DELETE FROM public.providers;
INSERT INTO public.providers (name, am, exposure, credit, terms, conf) SELECT name, am, exposure, credit, terms, conf FROM refresh_backup_20260909.providers;
DO $$ BEGIN IF EXISTS ((SELECT name, am, exposure, credit, terms, conf FROM public.providers EXCEPT ALL SELECT name, am, exposure, credit, terms, conf FROM refresh_backup_20260909.providers) UNION ALL (SELECT name, am, exposure, credit, terms, conf FROM refresh_backup_20260909.providers EXCEPT ALL SELECT name, am, exposure, credit, terms, conf FROM public.providers)) THEN RAISE EXCEPTION 'Rollback mismatch: providers'; END IF; END $$;
INSERT INTO public.customers (name, am, exposure, credit, terms, conf) SELECT name, am, exposure, credit, terms, conf FROM refresh_backup_20260909.customers;
DO $$ BEGIN IF EXISTS ((SELECT name, am, exposure, credit, terms, conf FROM public.customers EXCEPT ALL SELECT name, am, exposure, credit, terms, conf FROM refresh_backup_20260909.customers) UNION ALL (SELECT name, am, exposure, credit, terms, conf FROM refresh_backup_20260909.customers EXCEPT ALL SELECT name, am, exposure, credit, terms, conf FROM public.customers)) THEN RAISE EXCEPTION 'Rollback mismatch: customers'; END IF; END $$;
INSERT INTO public.carriers (name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp) SELECT name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp FROM refresh_backup_20260909.carriers;
DO $$ BEGIN IF EXISTS ((SELECT name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp FROM public.carriers EXCEPT ALL SELECT name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp FROM refresh_backup_20260909.carriers) UNION ALL (SELECT name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp FROM refresh_backup_20260909.carriers EXCEPT ALL SELECT name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp FROM public.carriers)) THEN RAISE EXCEPTION 'Rollback mismatch: carriers'; END IF; END $$;
INSERT INTO public.routes (id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur) SELECT id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur FROM refresh_backup_20260909.routes;
DO $$ BEGIN IF EXISTS ((SELECT id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur FROM public.routes EXCEPT ALL SELECT id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur FROM refresh_backup_20260909.routes) UNION ALL (SELECT id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur FROM refresh_backup_20260909.routes EXCEPT ALL SELECT id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur FROM public.routes)) THEN RAISE EXCEPTION 'Rollback mismatch: routes'; END IF; END $$;
INSERT INTO public.customer_routes (id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp) SELECT id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp FROM refresh_backup_20260909.customer_routes;
DO $$ BEGIN IF EXISTS ((SELECT id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp FROM public.customer_routes EXCEPT ALL SELECT id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp FROM refresh_backup_20260909.customer_routes) UNION ALL (SELECT id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp FROM refresh_backup_20260909.customer_routes EXCEPT ALL SELECT id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp FROM public.customer_routes)) THEN RAISE EXCEPTION 'Rollback mismatch: customer_routes'; END IF; END $$;
INSERT INTO public.am_breakdown (id, am, side, name, profit, calls, dur, rev, exp, routes, sec) SELECT id, am, side, name, profit, calls, dur, rev, exp, routes, sec FROM refresh_backup_20260909.am_breakdown;
DO $$ BEGIN IF EXISTS ((SELECT id, am, side, name, profit, calls, dur, rev, exp, routes, sec FROM public.am_breakdown EXCEPT ALL SELECT id, am, side, name, profit, calls, dur, rev, exp, routes, sec FROM refresh_backup_20260909.am_breakdown) UNION ALL (SELECT id, am, side, name, profit, calls, dur, rev, exp, routes, sec FROM refresh_backup_20260909.am_breakdown EXCEPT ALL SELECT id, am, side, name, profit, calls, dur, rev, exp, routes, sec FROM public.am_breakdown)) THEN RAISE EXCEPTION 'Rollback mismatch: am_breakdown'; END IF; END $$;
INSERT INTO public.am_totals (am, total_carriers) SELECT am, total_carriers FROM refresh_backup_20260909.am_totals;
DO $$ BEGIN IF EXISTS ((SELECT am, total_carriers FROM public.am_totals EXCEPT ALL SELECT am, total_carriers FROM refresh_backup_20260909.am_totals) UNION ALL (SELECT am, total_carriers FROM refresh_backup_20260909.am_totals EXCEPT ALL SELECT am, total_carriers FROM public.am_totals)) THEN RAISE EXCEPTION 'Rollback mismatch: am_totals'; END IF; END $$;
INSERT INTO public.daily_carrier (id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls) SELECT id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls FROM refresh_backup_20260909.daily_carrier;
DO $$ BEGIN IF EXISTS ((SELECT id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls FROM public.daily_carrier EXCEPT ALL SELECT id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls FROM refresh_backup_20260909.daily_carrier) UNION ALL (SELECT id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls FROM refresh_backup_20260909.daily_carrier EXCEPT ALL SELECT id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls FROM public.daily_carrier)) THEN RAISE EXCEPTION 'Rollback mismatch: daily_carrier'; END IF; END $$;
COMMIT;
SELECT 'providers' AS table_name, (SELECT count(*) FROM public.providers) AS live_rows, (SELECT count(*) FROM refresh_backup_20260909.providers) AS backup_rows
UNION ALL
SELECT 'customers' AS table_name, (SELECT count(*) FROM public.customers) AS live_rows, (SELECT count(*) FROM refresh_backup_20260909.customers) AS backup_rows
UNION ALL
SELECT 'carriers' AS table_name, (SELECT count(*) FROM public.carriers) AS live_rows, (SELECT count(*) FROM refresh_backup_20260909.carriers) AS backup_rows
UNION ALL
SELECT 'routes' AS table_name, (SELECT count(*) FROM public.routes) AS live_rows, (SELECT count(*) FROM refresh_backup_20260909.routes) AS backup_rows
UNION ALL
SELECT 'customer_routes' AS table_name, (SELECT count(*) FROM public.customer_routes) AS live_rows, (SELECT count(*) FROM refresh_backup_20260909.customer_routes) AS backup_rows
UNION ALL
SELECT 'am_breakdown' AS table_name, (SELECT count(*) FROM public.am_breakdown) AS live_rows, (SELECT count(*) FROM refresh_backup_20260909.am_breakdown) AS backup_rows
UNION ALL
SELECT 'am_totals' AS table_name, (SELECT count(*) FROM public.am_totals) AS live_rows, (SELECT count(*) FROM refresh_backup_20260909.am_totals) AS backup_rows
UNION ALL
SELECT 'daily_carrier' AS table_name, (SELECT count(*) FROM public.daily_carrier) AS live_rows, (SELECT count(*) FROM refresh_backup_20260909.daily_carrier) AS backup_rows;
