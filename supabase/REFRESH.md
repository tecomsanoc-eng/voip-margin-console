# Reviewed staging refresh and owner-controlled promotion

The normal refresh is `python scripts/build_weekly.py exports out`, dry-run validation
of all eight CSVs, then `python scripts/stage_refresh.py out --load`. The staging
loader replaces only the eight `_next` tables and checks all returned fields and
primary keys against the CSVs. Run `python scripts/stage_refresh.py out` to repeat
read-only verification. Staging loading itself is not atomic; after a failed load,
rerun the whole load and require a successful verification before promotion.
Do not run concurrent loaders. Do not use sequential direct-live CSV imports.

The 32 reviewed mappings include the original seven plus 25 owner-approved
aliases. NGN-Tec, PC GLOBAL-Tec, Sigma-Tec and Stream-Tec remain unresolved;
their candidate authoritative records remain separate. Ambiguous traffic is not
attributed to a guessed carrier. The non-TEC Voicekings identity remains in the
master roster; only Tec-Voicekings belongs in the TEC-only production dataset.

## Before production promotion

1. Obtain owner confirmation. Stop staging loaders and other refresh jobs.
2. Run `python scripts/stage_refresh.py out` and require success. This SQL is
   specific to the reviewed refresh counts; do not reuse for a different dataset.
3. Review both `supabase/promote_staging.sql` and `supabase/rollback_refresh.sql`.
   Ensure the database operator is `postgres` (or an equivalent privileged role)
   and can create the private backup schema. Keep database credentials out of Git.
4. The promotion creates `refresh_backup_20260909` and copies all eight old live
   tables inside the same transaction, before deleting any live rows. It refuses
   to overwrite an existing backup schema. Keep this backup until the owner
   accepts the production test. No backup or promotion has been executed by the
   refresh preparation workflow.

## Owner commands, after confirmation

From the repository in PowerShell, with `SUPABASE_DB_URL` set securely to the
Postgres connection string (not the REST URL or service-role API key):

```powershell
python scripts/stage_refresh.py out
# Continue only if verification exited successfully.
psql -X -v ON_ERROR_STOP=1 --dbname "$env:SUPABASE_DB_URL" -f supabase/promote_staging.sql
# Continue only if promotion exited successfully.
psql -X -v ON_ERROR_STOP=1 --dbname "$env:SUPABASE_DB_URL" -f supabase/verify_promotion.sql
```

Alternatively, use the Supabase SQL Editor as `postgres`: execute the **entire**
`promote_staging.sql` file as one query, then execute `verify_promotion.sql`.
Do not run selected individual statements. The script explicitly starts and
commits one transaction. An error aborts it; in an interactive session issue
`ROLLBACK;` before doing anything else. Do not continue past an error.

All eight live, staging and expected counts must match. Reload the console and
check carrier identities, AM views, routes and daily history. Carrier profit
includes both customer-side and provider-side attribution, so it must not be
interpreted as total company net profit. The build reports 87 unassigned carriers;
this is retained source ownership, not a new staging ownership assignment.
Customer-route reported profit has a small discrepancy from revenue minus
expense; the builder retains the source Profit field rather than recomputing it.
Review the financial totals supplied in the owner handoff.

The SQL locks live tables against concurrent writers and staging tables against
changes, preserves live tables/constraints/indexes/RLS/grants, uses explicit
columns, and checks live/staging equality before commit. It never drops a table
or modifies `_next`. Locks last through the transaction, as documented by
[PostgreSQL](https://www.postgresql.org/docs/current/explicit-locking.html).
Existing unexpected constraints or triggers may cause promotion to fail safely;
no constraints are disabled. Reads in a single snapshot see a consistent dataset;
independent requests spanning commit may observe different dataset versions.

## Rollback

If promotion fails, the whole transaction (including backup creation) rolls back;
no restore is needed. If the production test fails **after a successful commit**,
stop refresh jobs and run the following as the same privileged database operator:

```powershell
psql -X -v ON_ERROR_STOP=1 --dbname "$env:SUPABASE_DB_URL" -f supabase/rollback_refresh.sql
```

Or execute the entire rollback file in the SQL Editor. It restores all eight
live tables from `refresh_backup_20260909` in one transaction and verifies exact
row equality before commit. Its final query compares live and backup counts.
It preserves staging and the backup. Rollback replaces live data with the
pre-promotion snapshot, so any later live writes would be discarded: perform
it during the controlled production test while other writers remain stopped.
After rollback use its backup-count query, not the staging-count query, as the
acceptance check. Do not delete or rename the backup to bypass a failed preflight.

## Validation limitation

Python tests, build, all CSV dry runs, and complete remote staging read-back were
run. The promotion/rollback SQL has been reviewed but not execution-tested:
no local PostgreSQL runtime is installed, and live execution awaits the owner.
