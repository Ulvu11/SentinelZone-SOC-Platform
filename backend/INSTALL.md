# Native installation

Python 3.12 and PostgreSQL are required for production. Create the PostgreSQL database/role using your normal administrator process; do not give the application database superuser privileges. Use the fixed repository directory, not a VM snapshot.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock.txt
cp .env.example .env
# Fill .env. For a local PostgreSQL service use its local hostname in DATABASE_URL.
# DATABASE_URL password must be URL-encoded; never commit .env.
chmod 600 .env
python -c 'from app.config import get_settings; get_settings().validate_runtime(); print("configuration accepted")'
alembic upgrade head
alembic check
python -m app.cli create-user soc-admin admin
uvicorn app.main:app --host 127.0.0.1 --port 8003
```

PowerShell activation: `.venv\Scripts\Activate.ps1`; other Python/Alembic commands are the same. Store the generated user token immediately; it is shown once and only its hash is stored. Configure TLS via the Nginx template before remote access.

For isolated local demonstration only, set APP_ENV=development, DATABASE_URL to a writable SQLite file, and ALLOW_FIXTURES=true. Legacy mock routes additionally require ENABLE_LEGACY_MOCK_ROUTES=true. Fixture ingestion is TEST mode and not healthy production telemetry. Do not migrate a populated demo DB into production without reconciling historical test/fixture data.

Before filling .env in the deployment checkout, run `bash scripts/acceptance-test.sh` in the activated venv. For PostgreSQL acceptance use a separate clean checkout and dedicated disposable DB as described in POSTGRESQL_ACCEPTANCE.md; never point pytest TEST_DATABASE_URL at this installation's data.
