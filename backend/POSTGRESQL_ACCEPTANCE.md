# PostgreSQL live acceptance — OPEN GATE

**POSTGRESQL LIVE ACCEPTANCE = UNVERIFIED** for this release workspace. The environment could not install/start PostgreSQL because system account/privilege operations were restricted. No SQLite test or SQL compilation is presented as PostgreSQL execution.

## Prerequisites on your Ubuntu/PostgreSQL lab

Use a clean extracted checkout without .env (do not test inside a running deployment). Install Python 3.12, its venv support, and PostgreSQL client tools matching the server major version through your normal administration process. The database server must be reachable. Install the repository's exact dependency lock:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock.txt
python -m pip check
```

Create a dedicated, empty database ending in _test. The test role needs ownership/DDL privileges and CREATEDB only for the backup restore drill. Do not grant these elevated test privileges to the production application role. For a local server an administrator can run:

```bash
sudo -u postgres createuser --login --createdb --pwprompt sentinelzone_acceptance
sudo -u postgres createdb --owner=sentinelzone_acceptance sentinelzone_test
```

For a remote server, ask its administrator to create the equivalent role/database. Configure authentication/TLS normally; do not relax pg_hba.conf to trust for this test.

## One-command acceptance after setting the test URL

Supply the URL through a secret environment mechanism, or a hidden interactive prompt. Do not store it in source, reports or shell history. URL format: postgresql+psycopg://TEST_USER:URL_ENCODED_PASSWORD@TEST_HOST:5432/sentinelzone_test (append your required TLS options).

```bash
unset DATABASE_URL
read -r -s -p 'Disposable TEST_DATABASE_URL: ' TEST_DATABASE_URL
printf '\n'
export TEST_DATABASE_URL
bash scripts/postgres-acceptance.sh --allow-test-db-reset
unset TEST_DATABASE_URL
```

The script refuses missing acknowledgement, SQLite, an unsafe DB name, a DATABASE_URL collision, or any existing tables. It never automatically deletes an existing database. Use a fresh empty test database on each run; retained test rows after a run are disposable, not a deployable DB.

Checks: connection; populated revision 0002 REAL/TEST data; upgrade to 0003; preserved identities/modes; non-null tenant ownership; composite FKs/indexes; cross-tenant FK rejection/rollback; Alembic model/constraint parity; downgrade and data preservation; re-upgrade; full pytest suite on the PostgreSQL TEST_DATABASE_URL including advisory exclusion, SKIP LOCKED, tenant access, rollback, retry and backup/restore.

The migration probe cleans only its own generated application tables before pytest. Unit fixtures then recreate application tables repeatedly. Do not run another service against this test DB. The separate loopback HTTP smoke uses temporary SQLite and is labelled as such.

## Evidence and exit codes

- reports/postgresql.log, postgresql-tests.xml, postgresql-summary.json are written locally.
- Exit 0 / PostgreSQL PASS requires the whole suite to pass with no skips.
- Test failure or failed preflight is nonzero; any skip means PARTIAL/nonzero.
- A missing pg_dump/pg_restore causes a backup-drill skip; lack of CREATEDB fails that drill.
- Keep these reports with the actual server/version and run date after review for sensitive metadata.

Only successful execution on your lab can close this gate. Separately validate migration locking/duration, backup retention and restore permissions on a representative copy of your actual database before a production upgrade.
