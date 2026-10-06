# Architecture

The original modules remain: api, auth, connectors, db/repositories, normalization, incidents, notifications and services.

Connectors read upstream systems -> normalization preserves original_sensor and collector_path -> ingest merges evidence, records REAL asset/sensor observations and runs correlation -> incident and outbox writes share the caller's transaction -> dispatch locks pending rows and rechecks current delivery policy.

Tenant ownership is derived from a verified bearer token. Static bootstrap format is `token:username:role[:tenant]`; omitting tenant uses DEFAULT_TENANT_ID. Database users hold globally unique hashed tokens plus tenant ownership. The one pre-auth lookup uses a fixed token-hash query and never materializes a different tenant into the request's ORM identity map.

ORM tenant criteria cover reads, aggregates, updates and deletes. Write guards reject cross-tenant objects and tenant reassignment. Composite PK/FK constraints bind events, refs, incident links, notes, audits, notifications, attempts, proposals and snapshots. Every request/worker has a separate session. Role definitions are global; user assignments are tenant scoped. Core SQL is reserved for migration/backup and the fixed authentication lookup; new application data queries must use the scoped ORM path.

Events have a composite identity `(tenant_id, event_uid, execution_mode)`; incident-event FKs include tenant and mode. REAL and TEST are persisted separately. TEST never changes real asset/sensor inventory and cannot create action proposals. External TEST delivery is opt-in, Telegram only, to a separate test destination. REPLAY is rejected by live ingestion; the replay service evaluates copied events in an isolated temporary SQLite database without invoking the notification/action paths.

A deployment has one configured connector/delivery tenant. Other tenants can own/query their data, but cannot poll/hunt through that tenant's global upstream credentials or deliver through its recipients. To integrate multiple live tenants, run separately configured workers or add an explicit per-tenant secret/config store; do not share global credentials implicitly.

Replay snapshots and asset snapshots are immutable by ORM guards and database triggers in migration 0003. Event-set hashes are verified before evaluation. Case Pack exports existing state deterministically, with an integrity hash and no export-time timestamp. Empty optional MITRE/users/AI/action fields mean no such integration/data is present.

Sensor health is separate from connector reachability. A successful Splunk query does not refresh Suricata liveness. Fresh non-alert telemetry or a verified heartbeat does. Without an expected cadence, liveness is unknown; with cadence, the API derives healthy/degraded/offline from elapsed time. The persisted status records the last observation; current status is calculated when read.
