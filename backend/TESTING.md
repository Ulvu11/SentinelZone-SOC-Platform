# Tests

Use Python 3.12, a clean checkout without a production .env, and the exact lock file. httpx SOCKS support (`socksio==1.0.0`) is included in the lock; no manual missing dependency is required.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock.txt
python -m pip check
bash scripts/acceptance-test.sh
python -m pytest -q -ra --junitxml=reports/test-results.xml
python scripts/export_contracts.py --check
python scripts/check_secrets.py
```

The baseline behavior tests are retained. Intentional changes in their expectations: explicit fixture opt-in, fixture TEST/degraded status, scoped connector identities, default REAL views, and dispatch suppression counters. Recorded-live payloads in unit fixtures are mocks in an isolated test DB, not live acceptance evidence.

Regression modules cover production configuration, route exposure, no fixture fallback, occurrence dedup, mode/tenant isolation, dispatch suppression, filters, sensor liveness, immutable snapshots, Case Pack, Replay, What Changed, contract drift, protocol shape errors, DB composite constraints and data-preserving migrations. Existing RBAC, optimistic locking, retries, rollback, idempotency, pagination and backup tests still run.

The general acceptance script clears application environment settings and uses temporary development databases. It runs the full suite, populated migration round-trips, dependency/secret/contract checks and a real loopback Uvicorn smoke check. It refuses a checkout containing a production .env. Category results come from JUnit test outcomes, not hardcoded PASS labels. Results are written under reports/acceptance* and reports/runtime-smoke.json.

For PostgreSQL, create an empty dedicated database whose name ends in `_test`. **The suite drops application tables in TEST_DATABASE_URL. Never use your lab/production database.**

```bash
# Populate through a secure local environment mechanism; do not paste real credentials into reports.
export TEST_DATABASE_URL='postgresql+psycopg://TEST_USER:URL_ENCODED_PASSWORD@TEST_DB_HOST/sentinelzone_test'
bash scripts/postgres-acceptance.sh --allow-test-db-reset
```

See [POSTGRESQL_ACCEPTANCE.md](POSTGRESQL_ACCEPTANCE.md) for exact Ubuntu preparation and commands. The script refuses a nonempty DB before any writes and requires explicit disposable-DB acknowledgement. Marker `postgresql` covers advisory-lock exclusion and SKIP LOCKED dispatch. The rest of the regular suite also uses TEST_DATABASE_URL when supplied. Matching-version pg_dump/pg_restore and a test role with CREATEDB are needed for the backup drill; missing client binaries produce a skip, and insufficient permissions fail. Migration-data regressions retain SQLite coverage; the PostgreSQL script additionally performs populated REAL/TEST upgrade/downgrade/upgrade and constraint checks on PostgreSQL itself.

Any PostgreSQL-mode skip causes a PARTIAL result and nonzero exit status, never full acceptance PASS. Read the skip reasons. Locally, PostgreSQL live acceptance is UNVERIFIED, regardless of successful SQLite categories.

Measured results and remaining skips are in FIX_REPORT.md and reports/. The full suite must be run again on the target PostgreSQL environment before production acceptance. The included heuristic secret scan works on a ZIP checkout; it is not a comprehensive Gitleaks/security audit.
