# API contract

The authoritative generated contract is `docs/openapi.json`. Run `python scripts/export_contracts.py --check` to compare it with the runtime. No legacy `/api/*` path exists in the default contract.

Send `Authorization: Bearer <token>`. Authenticated identities include a tenant. A client-supplied tenant header/query/body cannot select another tenant. Cross-tenant object access returns 404; wrong role returns 403; absent/invalid credentials return 401. Roles remain viewer, analyst, operator and admin.

## Reads and filters

| Route | Semantics |
|---|---|
| GET /health | Public. 503 if DB unavailable; HTTP 200 can still contain `status=degraded`. |
| GET /v1/alerts | source, priority, host_id, from, to, limit, cursor, include_test. REAL by default. |
| GET /v1/alerts/{event_uid} | REAL by default; `execution_mode=TEST` selects the tenant's TEST copy. Includes all external refs. |
| GET /v1/overview | from/to bound event_time and incident opened_at. REAL only. |
| GET /v1/metrics | agent_id/from/to apply to event, incident, notification and asset aggregates. REAL only. |
| GET /v1/incidents | status, priority, cursor, limit, execution_mode (default REAL). |
| GET /v1/telemetry-health | read permission. Separate connector and sensor maps; current liveness status and last-seen. |
| GET /v1/incidents/{id}/case-pack | read permission. Stable JSON + content SHA-256 of the persisted incident snapshot. |
| GET /v1/assets/{host_id}/what-changed | read permission. Latest two inventory snapshots, or explicit before_id/after_id. |
| GET /v1/replay/rules | read permission. Published rule versions and parameters. |
| GET /v1/replay/{run_id} | read permission, tenant scoped. |

`from` and `to` require an explicit offset (`Z` or `+04:00` etc.), normalize to UTC, and use an inclusive start/exclusive end. Invalid, naive or inverted bounds return 422. Overview incident counts are by opened_at, notifications by created_at, and assets by last_seen. Agent-scoped incidents/notifications require a linked event from that agent. Cursor order is event_time, event_uid, execution_mode, all descending.

## New writes

| Route | Permission | Input |
|---|---|---|
| POST /v1/telemetry/heartbeat | admin | original_sensor, observed_at, optional host_id. Actual telemetry observation only. |
| POST /v1/assets/{host_id}/snapshots | admin | local_users, services, startup_items, unsigned_processes, outbound_destinations, telemetry_sources, criticality. |
| POST /v1/event-sets | replay (analyst/operator/admin) | event_uids and execution_mode REAL/TEST. Copies a bounded set into an immutable snapshot. |
| POST /v1/replay | replay | event_set_id, rule_id, old_version, new_version. Returns both deterministic results and run_at. |

Replay never dispatches notifications, executes actions, or writes production events/incidents. Version `1` uses a 15-minute correlation window; version `2` uses 5 minutes with the same scoring algorithm. A nonstandard configured live window is recorded as `1-window-N` and replay recognizes N=1..1440. Published versions must keep their implementation semantics stable; a future algorithm change requires a new implementation/version.

What Changed emits neutral change kinds, not a maliciousness verdict. Snapshots are full normalized inventory observations, not arbitrary raw logs. Missing two snapshots returns `data_complete=false`.

## Incident lifecycle and notifications

Existing transitions remain NEW -> INVESTIGATING -> CONTAINED -> RESOLVED. Optional RESOLVED -> CLOSED requires disposition; CLOSED is terminal. Patches still require If-Match; stale versions return 409 and absent If-Match returns 428. Added incident fields: tenant_id, execution_mode, summary, disposition, updated_at, rule_id, rule_version.

Notification rows include tenant_id, template_version, created_at, sent_at and suppression_reason. Existing enqueue-time SKIPPED rows are preserved. Dispatch-time denial produces SUPPRESSED with CHANNEL_DISABLED, LEGACY_NOTIFIER_ACTIVE or POLICY_DENIED, without calling the sender or incrementing attempts.

All existing assets, agents, admin, notes, timeline, merge, notifications, hunts and proposal routes remain. See the generated endpoint inventory in `FIX_REPORT.md` for the full list.
