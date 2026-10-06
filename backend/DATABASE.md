# Database and migration

Production requires PostgreSQL using the installed synchronous `postgresql+psycopg` driver. Bare `postgresql://` URLs are normalized to that driver. SQLite is development/test only. Alembic head: **0003**.

```bash
alembic current
alembic upgrade head
alembic check
```

Revision 0003 incrementally changes the original schema. It retains original event UIDs and incident IDs, backfills tenant ownership from DEFAULT_TENANT_ID (lab by default), derives event execution mode from is_test, adds composite keys/FKs and ref uniqueness, and adds sensor_state, event_sets, replay_runs and asset_snapshots. It copies title into summary and last_seen into updated_at for existing incidents. TEST-only legacy pending external notifications are suppressed.

Back up first and use a maintenance window: SQLite's batch operations rebuild affected tables. PostgreSQL alters keys/constraints and takes locks. `migrations/schema_0002.py` and `schema_0003.py` freeze revision metadata; never replace them with imports of current application models.

A historical incident containing both REAL and TEST events is detected **before schema changes** and upgrade stops. Reconcile it from original evidence before retrying; the migration does not guess a real priority or delete evidence. Historical fixtures that were previously inserted with is_test=false cannot be distinguished automatically: rebuild a demo database or explicitly reconcile those rows before production use.

Downgrading removes the new investigation/telemetry tables. Export/back up first. Downgrade refuses identities that would collide under the old tenant-less/mode-less keys. New production data should not be downgraded casually.

Composite DB foreign keys protect tenant/mode links; SQLite connections used by the application and regular unit-test fixture enable foreign_keys. PostgreSQL ingest uses a transaction advisory lock; outbox uses FOR UPDATE SKIP LOCKED. Those two PostgreSQL-only concurrency checks require a real disposable PostgreSQL test database.

All data tables except the global roles vocabulary have a non-null indexed tenant_id. Incident merge targets also have a tenant/mode composite self-FK. Generic audit_log records are tenant-scoped, while incident_audit has an incident FK. Event/incident host_id is an observed identity, not a forced asset FK: unresolved network assets can legitimately precede inventory.

Revision 0003 only reshapes managed application tables and leaves unrelated tables/constraints untouched. Shared external FKs referencing changed application keys may block migration and must be reviewed before deployment; a dedicated application database is preferred. PostgreSQL constraint-owned indexes and named checks are handled separately from ordinary indexes. Actual PostgreSQL DDL execution remains an open acceptance gate, documented in POSTGRESQL_ACCEPTANCE.md.

The backup utility is a validation convenience, not a retention policy. Use your established encrypted PostgreSQL backups and restore drills. No database dump or runtime database is included in the fixed ZIP.
