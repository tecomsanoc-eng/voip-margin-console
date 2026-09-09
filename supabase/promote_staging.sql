-- OWNER-EXECUTED ONLY. Run the entire file on one connection as postgres.
-- Any error aborts the transaction. With psql use -X -v ON_ERROR_STOP=1.
-- Stop staging loaders and other refresh jobs until promotion completes.
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '5min';

LOCK TABLE public.providers, public.customers, public.carriers, public.routes, public.customer_routes, public.am_breakdown, public.am_totals, public.daily_carrier IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE public.providers_next, public.customers_next, public.carriers_next, public.routes_next, public.customer_routes_next, public.am_breakdown_next, public.am_totals_next, public.daily_carrier_next IN SHARE MODE;
-- This unique backup schema intentionally makes repeated promotion fail.
CREATE SCHEMA refresh_backup_20260909;
REVOKE ALL ON SCHEMA refresh_backup_20260909 FROM PUBLIC, anon, authenticated;
DO $$ BEGIN IF (SELECT count(*) FROM public.providers_next) <> 188 THEN RAISE EXCEPTION 'Unexpected staging count: providers'; END IF; END $$;
CREATE TABLE refresh_backup_20260909.providers AS TABLE public.providers;
DO $$ BEGIN IF (SELECT count(*) FROM public.customers_next) <> 165 THEN RAISE EXCEPTION 'Unexpected staging count: customers'; END IF; END $$;
CREATE TABLE refresh_backup_20260909.customers AS TABLE public.customers;
DO $$ BEGIN IF (SELECT count(*) FROM public.carriers_next) <> 419 THEN RAISE EXCEPTION 'Unexpected staging count: carriers'; END IF; END $$;
CREATE TABLE refresh_backup_20260909.carriers AS TABLE public.carriers;
DO $$ BEGIN IF (SELECT count(*) FROM public.routes_next) <> 5025 THEN RAISE EXCEPTION 'Unexpected staging count: routes'; END IF; END $$;
CREATE TABLE refresh_backup_20260909.routes AS TABLE public.routes;
DO $$ BEGIN IF (SELECT count(*) FROM public.customer_routes_next) <> 7281 THEN RAISE EXCEPTION 'Unexpected staging count: customer_routes'; END IF; END $$;
CREATE TABLE refresh_backup_20260909.customer_routes AS TABLE public.customer_routes;
DO $$ BEGIN IF (SELECT count(*) FROM public.am_breakdown_next) <> 276 THEN RAISE EXCEPTION 'Unexpected staging count: am_breakdown'; END IF; END $$;
CREATE TABLE refresh_backup_20260909.am_breakdown AS TABLE public.am_breakdown;
DO $$ BEGIN IF (SELECT count(*) FROM public.am_totals_next) <> 36 THEN RAISE EXCEPTION 'Unexpected staging count: am_totals'; END IF; END $$;
CREATE TABLE refresh_backup_20260909.am_totals AS TABLE public.am_totals;
DO $$ BEGIN IF (SELECT count(*) FROM public.daily_carrier_next) <> 3245 THEN RAISE EXCEPTION 'Unexpected staging count: daily_carrier'; END IF; END $$;
CREATE TABLE refresh_backup_20260909.daily_carrier AS TABLE public.daily_carrier;
DELETE FROM public.daily_carrier;
DELETE FROM public.am_totals;
DELETE FROM public.am_breakdown;
DELETE FROM public.customer_routes;
DELETE FROM public.routes;
DELETE FROM public.carriers;
DELETE FROM public.customers;
DELETE FROM public.providers;
INSERT INTO public.providers (name, am, exposure, credit, terms, conf) SELECT name, am, exposure, credit, terms, conf FROM public.providers_next;
DO $$ BEGIN IF EXISTS ((SELECT name, am, exposure, credit, terms, conf FROM public.providers EXCEPT ALL SELECT name, am, exposure, credit, terms, conf FROM public.providers_next) UNION ALL (SELECT name, am, exposure, credit, terms, conf FROM public.providers_next EXCEPT ALL SELECT name, am, exposure, credit, terms, conf FROM public.providers)) THEN RAISE EXCEPTION 'Live/staging mismatch: providers'; END IF; END $$;
INSERT INTO public.customers (name, am, exposure, credit, terms, conf) SELECT name, am, exposure, credit, terms, conf FROM public.customers_next;
DO $$ BEGIN IF EXISTS ((SELECT name, am, exposure, credit, terms, conf FROM public.customers EXCEPT ALL SELECT name, am, exposure, credit, terms, conf FROM public.customers_next) UNION ALL (SELECT name, am, exposure, credit, terms, conf FROM public.customers_next EXCEPT ALL SELECT name, am, exposure, credit, terms, conf FROM public.customers)) THEN RAISE EXCEPTION 'Live/staging mismatch: customers'; END IF; END $$;
INSERT INTO public.carriers (name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp) SELECT name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp FROM public.carriers_next;
DO $$ BEGIN IF EXISTS ((SELECT name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp FROM public.carriers EXCEPT ALL SELECT name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp FROM public.carriers_next) UNION ALL (SELECT name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp FROM public.carriers_next EXCEPT ALL SELECT name, role, am, dur, calls, rev, profit, due, netbal, curexp, exp FROM public.carriers)) THEN RAISE EXCEPTION 'Live/staging mismatch: carriers'; END IF; END $$;
INSERT INTO public.routes (id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur) SELECT id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur FROM public.routes_next;
DO $$ BEGIN IF EXISTS ((SELECT id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur FROM public.routes EXCEPT ALL SELECT id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur FROM public.routes_next) UNION ALL (SELECT id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur FROM public.routes_next EXCEPT ALL SELECT id, destination, provider, trunk, lcr, buy, sell, profit, profit_pct, asr, acd, calls, dur FROM public.routes)) THEN RAISE EXCEPTION 'Live/staging mismatch: routes'; END IF; END $$;
INSERT INTO public.customer_routes (id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp) SELECT id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp FROM public.customer_routes_next;
DO $$ BEGIN IF EXISTS ((SELECT id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp FROM public.customer_routes EXCEPT ALL SELECT id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp FROM public.customer_routes_next) UNION ALL (SELECT id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp FROM public.customer_routes_next EXCEPT ALL SELECT id, customer, destination, provider, sell, buy, profit, profit_pct, asr, acd, calls, dur, rev, exp FROM public.customer_routes)) THEN RAISE EXCEPTION 'Live/staging mismatch: customer_routes'; END IF; END $$;
INSERT INTO public.am_breakdown (id, am, side, name, profit, calls, dur, rev, exp, routes, sec) SELECT id, am, side, name, profit, calls, dur, rev, exp, routes, sec FROM public.am_breakdown_next;
DO $$ BEGIN IF EXISTS ((SELECT id, am, side, name, profit, calls, dur, rev, exp, routes, sec FROM public.am_breakdown EXCEPT ALL SELECT id, am, side, name, profit, calls, dur, rev, exp, routes, sec FROM public.am_breakdown_next) UNION ALL (SELECT id, am, side, name, profit, calls, dur, rev, exp, routes, sec FROM public.am_breakdown_next EXCEPT ALL SELECT id, am, side, name, profit, calls, dur, rev, exp, routes, sec FROM public.am_breakdown)) THEN RAISE EXCEPTION 'Live/staging mismatch: am_breakdown'; END IF; END $$;
INSERT INTO public.am_totals (am, total_carriers) SELECT am, total_carriers FROM public.am_totals_next;
DO $$ BEGIN IF EXISTS ((SELECT am, total_carriers FROM public.am_totals EXCEPT ALL SELECT am, total_carriers FROM public.am_totals_next) UNION ALL (SELECT am, total_carriers FROM public.am_totals_next EXCEPT ALL SELECT am, total_carriers FROM public.am_totals)) THEN RAISE EXCEPTION 'Live/staging mismatch: am_totals'; END IF; END $$;
INSERT INTO public.daily_carrier (id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls) SELECT id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls FROM public.daily_carrier_next;
DO $$ BEGIN IF EXISTS ((SELECT id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls FROM public.daily_carrier EXCEPT ALL SELECT id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls FROM public.daily_carrier_next) UNION ALL (SELECT id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls FROM public.daily_carrier_next EXCEPT ALL SELECT id, carrier, day, cust_rev, cust_profit, cust_dur, cust_calls, prov_exp, prov_profit, prov_dur, prov_calls FROM public.daily_carrier)) THEN RAISE EXCEPTION 'Live/staging mismatch: daily_carrier'; END IF; END $$;
COMMIT;
-- Promotion committed. Run supabase/verify_promotion.sql.
