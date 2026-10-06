# SentinelZone SOC Backend — 0.28.0 fixed

Incremental fixes to the existing FastAPI / SQLAlchemy / Alembic / PostgreSQL / Pydantic / httpx backend. Covers Phase 24, Phase 26 investigation features and Phase 27 notifications. No VM image or lab IP is required.

## Start with Docker Compose

```bash
cp .env.example .env
# Fill PostgreSQL password and DATABASE_URL (hostname postgres inside Compose).
# Fill auth/connectors/CA paths and frontend origin as appropriate. Keep delivery disabled initially.
docker compose up -d --build
docker compose exec backend python -m app.cli create-user soc-admin admin
curl --fail-with-body http://127.0.0.1:8003/health
```

The create-user command prints a random token once. Store it securely. An empty AUTH_TOKENS is valid when database authentication is enabled. Until a DB user is created, protected endpoints deny access. A missing connector is `not_configured`; it cannot supply fixture data in production.

Native installation is in [INSTALL.md](INSTALL.md). TLS/reverse proxy and management/VPN restrictions are in [DEPLOYMENT.md](DEPLOYMENT.md). Do not expose the backend's raw port to an untrusted network.

## Behavior

- Default `/v1/*` routes require a bearer identity and the existing viewer / analyst / operator / admin roles. Public `/health` reports database and connector status.
- Legacy `/api/*` mock routes are disabled by default and forbidden in production. Development requires an explicit flag.
- Fixture ingestion requires development/test plus `ALLOW_FIXTURES=true`. It produces TEST events, degraded connector status, and incomplete data, never real telemetry.
- Native event identities are scoped by tenant and execution mode. Duplicate collector evidence is merged without new events/incidents/notifications.
- REAL and TEST correlation are isolated; the default alert, incident, overview and metrics views are REAL. Explicit TEST reads remain available.
- Channels and migration policy are checked again at dispatch. Queued messages denied by current policy become SUPPRESSED.
- Time filters use aware UTC timestamps and half-open `[from,to)` intervals; invalid/naive timestamps return 422.
- Sensor liveness uses telemetry/heartbeats and configured expected intervals. No alerts alone does not establish a blind spot.
- Case Pack exports stable JSON; Replay uses immutable event snapshots and a versioned rule in an isolated temporary database; What Changed compares inventory snapshots as investigation context.

## Validation and integration

[TESTING.md](TESTING.md), [FIX_REPORT.md](FIX_REPORT.md), and `reports/` contain reproducible tests and measured results. [REAL_CONNECTOR_ACCEPTANCE.md](REAL_CONNECTOR_ACCEPTANCE.md) gives the lab acceptance procedure. **Live Splunk, Wazuh and CryptoGuard integration has not been tested here.** In particular, the Wazuh alerts contract requires verification/an adapter.

Schema head is `0003`. Back up before upgrading an existing deployment. Read [DATABASE.md](DATABASE.md) for tenant backfill, historical test data and downgrade restrictions.

In a clean source checkout, `bash scripts/acceptance-test.sh` runs isolated acceptance and prints the category matrix plus exact pytest counts. PostgreSQL live acceptance remains UNVERIFIED here; use [POSTGRESQL_ACCEPTANCE.md](POSTGRESQL_ACCEPTANCE.md) and `bash scripts/postgres-acceptance.sh --allow-test-db-reset` against a dedicated empty test database.
