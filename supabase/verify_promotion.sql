SELECT 'providers' AS table_name, (SELECT count(*) FROM public.providers) AS live_rows, (SELECT count(*) FROM public.providers_next) AS staging_rows, 188 AS expected_rows
UNION ALL
SELECT 'customers' AS table_name, (SELECT count(*) FROM public.customers) AS live_rows, (SELECT count(*) FROM public.customers_next) AS staging_rows, 165 AS expected_rows
UNION ALL
SELECT 'carriers' AS table_name, (SELECT count(*) FROM public.carriers) AS live_rows, (SELECT count(*) FROM public.carriers_next) AS staging_rows, 419 AS expected_rows
UNION ALL
SELECT 'routes' AS table_name, (SELECT count(*) FROM public.routes) AS live_rows, (SELECT count(*) FROM public.routes_next) AS staging_rows, 5025 AS expected_rows
UNION ALL
SELECT 'customer_routes' AS table_name, (SELECT count(*) FROM public.customer_routes) AS live_rows, (SELECT count(*) FROM public.customer_routes_next) AS staging_rows, 7281 AS expected_rows
UNION ALL
SELECT 'am_breakdown' AS table_name, (SELECT count(*) FROM public.am_breakdown) AS live_rows, (SELECT count(*) FROM public.am_breakdown_next) AS staging_rows, 276 AS expected_rows
UNION ALL
SELECT 'am_totals' AS table_name, (SELECT count(*) FROM public.am_totals) AS live_rows, (SELECT count(*) FROM public.am_totals_next) AS staging_rows, 36 AS expected_rows
UNION ALL
SELECT 'daily_carrier' AS table_name, (SELECT count(*) FROM public.daily_carrier) AS live_rows, (SELECT count(*) FROM public.daily_carrier_next) AS staging_rows, 3245 AS expected_rows;
