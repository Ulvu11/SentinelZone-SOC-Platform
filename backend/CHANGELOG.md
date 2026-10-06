# Changelog

## 0.28.0 — production isolation fixes

- Explicit development-only mock and fixture gates; fail-closed PostgreSQL/production configuration.
- Canonical Suricata occurrence IDs; idempotent multi-collector evidence merge.
- Tenant-scoped ORM reads/writes plus composite database constraints; isolated REAL/TEST incident correlation and inventory; replay blocked from live ingest.
- Dispatch-time channel/legacy/canary/tenant/test policy with SUPPRESSED reasons and versioned safe payloads.
- UTC from/to filtering and agent-scoped metrics; original sensor liveness and heartbeat API.
- Stable Case Pack JSON; immutable event sets, versioned deterministic replay results; neutral What Changed snapshot comparison.
- Incident summary, disposition, updated_at and optional terminal CLOSED state.
- Alembic 0003 with preserved IDs/data, historical-mode checks and snapshot immutability triggers.
- Non-root Docker/Compose, TLS/VPN proxy guidance, portable secret scan and real connector acceptance steps.
- Regenerated OpenAPI/contracts and added production, boundary, investigation, migration and HTTP-shape regression suites.
- Final tenant/mode merge FKs, all-model tenant/FK/index checks, unrelated-table migration preservation, and PostgreSQL constraint-name/index handling.
- Isolated acceptance scripts with measured JUnit category results, real Uvicorn smoke, guarded PostgreSQL round-trip/full-suite runner, runtime-generated test identities and explicit open live-integration gates.

## 0.27.0 — supplied baseline

Original Phase 24/26/27 backend, notification outbox, deployment templates and 60 baseline tests. Retained architecture and supported roles.
