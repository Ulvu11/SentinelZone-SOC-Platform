# SentinelZone SIEM Backend — fixed release 0.28.0

Tarix: 2026-10-06. Mənbə: təqdim edilmiş SIEM-Backend repository-si və yarımçıq qalmış düzəlişlərin davamı. Arxitektura sıfırdan yazılmayıb; FastAPI, SQLAlchemy, Alembic, PostgreSQL, Pydantic, httpx və pytest saxlanılıb.

## Yekun ölçülmüş nəticə

| Yoxlama | Nəticə |
|---|---|
| Tam pytest suite | **172 passed / 0 failed / 2 skipped** |
| Production startup/config regression seçimi | **20 passed / 0 failed / 0 skipped** |
| Acceptance category matrix | Bütün lokal kateqoriyalar PASS; reports/acceptance-summary.json |
| Ayrı Uvicorn prosesi, real loopback HTTP | PASS; reports/runtime-smoke.json |
| Runtime OpenAPI və saxlanmış contract | Eynidir: **36 path / 40 HTTP əməliyyatı** |
| Alembic head | **0003** |
| Populated upgrade → downgrade → upgrade, SQLite | PASS; REAL/TEST data və ID preservation |
| Model/schema parity, FK/index/unique yoxlamaları | PASS, lokal SQLite; Alembic check drift tapmadı |
| Dependency lock / pip check | PASS; socksio==1.0.0 lock-a daxildir |
| Portable secret scan | PASS, heuristic scan; tam security audit deyil |
| PostgreSQL canlı acceptance | **UNVERIFIED** |
| Real Splunk / Wazuh / CryptoGuard | **UNVERIFIED** |
| Docker build/run, systemd execution, nginx -t | Target host-da UNVERIFIED; statik fayllar yoxlanılıb |

Tam çıxış: reports/acceptance.log və reports/acceptance-tests.xml. Production seçimi: reports/production-validation.xml. reports/pytest.txt və reports/test-results.xml son tam run-un surətləridir. Testlərdə bir Starlette TestClient/httpx deprecation warning var; test failure deyil. Lock-u qorumaq üçün yoxlanılmamış dependency upgrade edilməyib.

Skip-lər:

1. test_postgresql_outbox_skip_locked — PostgreSQL FOR UPDATE SKIP LOCKED tələb edir.
2. test_ingest_lock_blocks_second_worker — PostgreSQL advisory lock tələb edir.

ZIP-də .git olmadığından secret scan artıq skip edilmir. O, repository faylları üzərində həqiqətən işləyir. PostgreSQL qurulması bu workspace-də sistem privilege/account əməliyyatları məhdud olduğundan mümkün olmayıb; bu nəticə gizlədilmir və PASS sayılmır.

## P0/P1 və feature düzəlişləri

| Mövzu | Konkret davranış |
|---|---|
| Legacy mock API | Default bağlıdır. Yalnız explicit development flag ilə açılır. Production flag true olduqda startup rədd edilir; normal production app-də route-lar yoxdur. |
| Fixture fallback | URL boşluğu fixture seçmir. Yalnız development/test + ALLOW_FIXTURES. Production missing URL → not_configured, data_complete=false. Fixture ingestion TEST/degraded olur. |
| Production config | PostgreSQL/psycopg məcburidir; SQLite/missing URL, mock, fixture, debug, wildcard CORS+credentials, yarımçıq connector/provider config və yararsız bootstrap auth rədd edilir. DB-auth mode istifadəçisiz deny-by-default başlayır. |
| Suricata occurrence UID | Flow/signature ilə məhdudlaşmır: canonical precise UTC timestamp, sensor identity və invariant event/traffic context daxildir. Collector metadata UID-yə daxil edilmir. Ayrı occurrence saxlanılır. |
| REAL/TEST/REPLAY | Tenant və mode üzrə ayrı identities/correlation. TEST real priority/confidence/asset/sensor state-i dəyişmir. REPLAY live ingest-ə daxil edilmir, ayrıca sandbox-da işləyir. |
| Dispatch-time policy | Telegram/SMS disable, legacy notifier, tenant/canary/test policy yenidən yoxlanır. İcazəsiz queued mesaj SUPPRESSED olur; sender çağırılmır. TEST chat real chat ilə eyni ola bilməz. |
| API filter-ləri | UTC-aware from/to, source, agent_id və cursor/limit SQL query-lərə tətbiq olunur. [from,to) intervalı; invalid/naive/reversed timestamp → 422. Combined source/time/pagination testi də var. |
| Evidence dedup | Event eyni qalır; collector_path union və yeni external_ref əlavə olunur. Composite unique constraint eyni reference-in təkrarını önləyir. |
| Sensor health | Connector reachability-dən ayrıdır. original_sensor, last alert/telemetry, expected interval, affected assets; heartbeat və non-alert telemetry qəbul edilir. Splunk healthy ikən Suricata offline ola bilər. |
| Tenant isolation | Bütün data modellərində indexed non-null tenant_id; authenticated identity-dən tenant binding; ORM select/aggregate/update/delete scope və write guards. Composite FK-lər cross-tenant child links-i rədd edir. |
| Incident model | Summary, disposition, updated_at, rule/version; mövcud lifecycle qorunur, optional RESOLVED→CLOSED disposition tələb edir. Optimistic If-Match, notes, audit, timeline və merge regression-ları keçir. |
| Case Pack | Deterministic JSON, persisted timestamps, tenant/mode, evidence refs, correlation, notes, proposal context, disposition və SHA-256. Output keys və hash test edilir. |
| Replay | Immutable hashed event set; rule_id/version seçimi; old/new nəticə və run_at saxlanır. Təkrar nəticə deterministikdir; live incident, outbox və action state dəyişmir. |
| What Changed | İki full inventory snapshot arasında yeni user/service/startup/unsigned process/destination, telemetry stopped və criticality fərqləri. Malicious verdict çıxarmır. |
| Notification model | Tenant, template_version, created_at/sent_at, suppression_reason. Fixed payload allowlist raw logs, passwords, tokens və honeypot credentials-i daşımır. |
| Health | HTTP 200 avtomatik healthy demək deyil. Real Uvicorn smoke-də DB healthy, connector-lar not_configured, ümumi status degraded oldu. DB outage ayrıca 503 test edilir. |
| Migrations | 0003 tenant/mode backfill, composite constraints, snapshots/triggers. Köhnə REAL+TEST mixed incident upgrade-dən əvvəl bloklanır. Başqa tətbiq cədvəlləri və FK-ləri silinmir. |
| Deploy | Non-root Docker, readonly Compose, capability drop, local bind, runtime env; systemd hardening; TLS Nginx və optional MGMT/VPN allowlist. |
| RBAC | viewer/analyst/operator/admin saxlanılıb. Unauthenticated 401, wrong role 403, foreign tenant object 404. Yeni endpointlər də permission tələb edir. |

### Tenant model audit

events, assets, external_refs, incident_candidates, incidents, incident_events, incident_notes, incident_audit, audit_log, notifications, notification_attempts, action_proposals, merge_requests, users, connector_state, sensor_state, event_sets, replay_runs və asset_snapshots tenant-scoped-dur. Yalnız roles global permission vocabulary-dir.

Event identity: tenant_id + event_uid + execution_mode. Event reference və incident-event FK-ləri mode-u da daşıyır. Incident merge target üçün tenant/mode self-FK əlavə edilib. Notes/audit/proposal/notification/replay/snapshot FK-ləri tenant sərhədini saxlayır. Event/incident host_id unresolved sensor identity ola bildiyi üçün məcburi asset FK deyil; generic audit_log isə konkret incident foreign key-si olmayan tenant-scoped auditdir.

Bu application/DB relationship isolation-dır, PostgreSQL RLS deyil. Birbaşa database administrator access-i ayrıca etibar sərhədidir. Raw Core SQL migration/backup və fixed pre-auth token lookup-la məhdud saxlanmalıdır.

## Dəyişdirilmiş fayllar

**Bütün əlavə/dəyişdirilmiş/silinmiş faylların dəqiq siyahısı reports/changed-files.txt-dədir**; original uploaded ZIP ilə byte/hash müqayisəsindən yaranır. reports/SHA256SUMS final source fayllarının yoxlama siyahısıdır. Qısa qruplaşdırma:

- app/config.py, main.py, ingest.py, scheduler.py, cli.py, backup.py — guard-lar, orchestration və təhlükəsiz backup drill.
- app/db/models.py, session.py, tenancy.py, repositories/* — tenant/mode schema, scope, evidence və filter-lər.
- app/connectors/*, normalization/models.py, normalization/suricata.py — explicit mode, protocol/error handling və occurrence identity.
- app/api/*, auth/*, schemas/* — API filter, RBAC, tenant access, investigation və telemetry endpointləri.
- app/incidents/*, notifications/*, services/telemetry.py, services/what_changed.py — lifecycle, replay/export, policy və sensor/inventory context.
- migrations/schema_0002.py, schema_0003.py, versions/0003_production_isolation.py — frozen migration metadata və upgrade/downgrade. 0002 role seed literal olaraq dondurulub; gələcək app permission dəyişikliklərini import etmir.
- tests/conftest.py, mövcud regression expectations və yeni production/boundary/investigation/migration/contract/release test modulları.
- scripts/acceptance-test.sh, postgres-acceptance.sh, acceptance.py, runtime-smoke.py, connector-acceptance.py, export_contracts.py, check_secrets.py, build-release.py və compatibility wrapper-lər.
- .env.example, .dockerignore, Dockerfile, docker-compose.yml, deploy/*, requirements*, pytest.ini, contracts/* və docs/openapi.json.
- README, API, ARCHITECTURE, DATABASE, INSTALL, DEPLOYMENT, TESTING, CHANGELOG, REAL_CONNECTOR_ACCEPTANCE, POSTGRESQL_ACCEPTANCE, bu hesabat və reports/*.

Heç bir real credential verilməyib və kodda real lab credential hardcode edilməyib. Reusable test auth/provider token-ləri test zamanı random yaranır. Negative-validation testlərində bilərəkdən yararsız markerlər, fixture-lərdə isə redacted password marker və sintetik lab payload-ları qalır; bunlar deploy credential deyil. Production .env, DB dump, private key, venv/cache və .git ZIP-ə daxil edilmir.

## OpenAPI endpoint inventory

Default runtime-da 36 path / 40 əməliyyat:

```text
GET   /health
GET   /v1/alerts
GET   /v1/alerts/{event_uid}
GET   /v1/overview
GET   /v1/assets
PATCH /v1/assets/{host_id}
POST  /v1/assets/{host_id}/snapshots
GET   /v1/assets/{host_id}/what-changed
GET   /v1/agents
GET   /v1/metrics
GET   /v1/telemetry-health
POST  /v1/telemetry/heartbeat
GET   /v1/incidents
POST  /v1/incidents
GET   /v1/incidents/{incident_id}
PATCH /v1/incidents/{incident_id}
GET   /v1/incidents/{incident_id}/timeline
POST  /v1/incidents/{incident_id}/notes
POST  /v1/incidents/{incident_id}/merge
GET   /v1/incidents/{incident_id}/case-pack
POST  /v1/event-sets
GET   /v1/replay/rules
POST  /v1/replay
GET   /v1/replay/{run_id}
GET   /v1/merge-requests
POST  /v1/merge-requests/{mid}/approve
POST  /v1/merge-requests/{mid}/reject
GET   /v1/notifications
POST  /v1/notifications/dispatch
POST  /v1/hunts/{approved_query_id}/run
POST  /v1/admin/ingest/run
GET   /v1/admin/users
POST  /v1/admin/users
PATCH /v1/admin/users/{username}
POST  /v1/admin/users/{username}/rotate-token
GET   /v1/admin/roles
GET   /v1/action-proposals
POST  /v1/action-proposals
POST  /v1/action-proposals/{proposal_id}/approve
POST  /v1/action-proposals/{proposal_id}/reject
```

FastAPI utility pages /docs, /redoc, /openapi.json və schema-dan gizlədilmiş / bu business-contract sayına daxil deyil. Legacy mock API default contract-da yoxdur.

## Təkrar icra

Clean extracted checkout, Python 3.12 venv və requirements.lock.txt quraşdırıldıqdan sonra:

```bash
bash scripts/acceptance-test.sh
```

PostgreSQL üçün POSTGRESQL_ACCEPTANCE.md-dəki setup-dan sonra, yalnız empty disposable *_test DB URL-i TEST_DATABASE_URL-də olduqda:

```bash
bash scripts/postgres-acceptance.sh --allow-test-db-reset
```

Script explicit acknowledgement, PostgreSQL driver, DB name, production URL collision və empty DB guard-larını yoxlayır. Sonra populated migrations, head, FK/index/model parity, tenant isolation, advisory/SKIP LOCKED, rollback, backup və tam suite işləyir. Heç bir PostgreSQL skip tam PASS kimi təqdim edilmir.

## Known limitations və OPEN GATES

1. **PostgreSQL live acceptance açıqdır.** PostgreSQL DDL, named constraints/indexes, locking və transaction concurrency real serverdə yoxlanmalıdır. SQLite uğuru bunları sübut etmir.
2. **Splunk real acceptance açıqdır:** TLS/CA, read-only capability, index/sourcetype mapping, window/pagination bounds, upstream timestamps və collector refs. Sorgu/error contract testləri mock HTTP ilədir.
3. **Wazuh real acceptance açıqdır:** standart Manager-də /alerts mövcudluğu iddia edilmir. Sənədləşdirilmiş alerts adapter/API contract-ı real sisteminizlə uyğunlaşdırılmalıdır; endpoint/env dəyişiklikdən əlavə adapter işi lazım ola bilər.
4. **CryptoGuard real acceptance açıqdır:** telemetry endpoint, read key, JSON/items/cursor contract-ı və real field mapping təsdiqlənməlidir.
5. **Telegram canary və SMS canlı acceptance açıqdır:** heç bir real mesaj göndərilməyib. Legacy routing overlap ayrıca aradan qaldırılmalıdır. DB outbox idempotentdir, amma provider send-dən sonra DB commit-dən əvvəl crash baş verərsə external delivery at-least-once-dur; exactly-once zəmanəti yoxdur.
6. **Deployment host gate:** Docker build/up, read-only filesystem, volume/secret permissions, nginx -t, sertifikat, VPN allowlist, firewall və proxy peer ünvanları yoxlanmalıdır.
7. **Telemetry/inventory integration:** heartbeat cadence və sensor ID-ni real feed müəyyən etməlidir. No alerts təkbaşına no telemetry deyil. What Changed full inventory snapshot qəbul edir; avtomatik OS inventory collector bu backend-də uydurulmayıb.
8. **Tenant integrations:** query/model isolation var; upstream/provider settings bir configured tenant üçündür. Çoxlu canlı tenant üçün ayrı configured worker deployment və ya ayrıca tenant-secret store lazımdır.
9. **Replay rule scope:** built-in asset-correlation v1/v2 və versioned custom window-lar; arbitrary uploaded rule/plugin engine deyil. Rule implementation dəyişdikdə yeni version tətbiq edilməlidir. Böyük dataset/load acceptance ayrıca aparılmalıdır.
10. **Case Pack optional data:** users/MITRE/AI references məlumatı olmadıqda boşdur. Actions performed boşdur, çünki proposal approval SOAR execution deyil. Bu release real SOAR executor əlavə etmir.
11. **Historical data:** REAL+TEST mixed incident migration-u dayandırır. Əvvəllər is_test=false kimi saxlanmış fixture data avtomatik tanınmır. Upgrade-dən əvvəl backup və reconciliation tələb olunur; downgrade yeni feature tables-i silir və identity collision olduqda rədd edilir.
12. **Frontend:** mövcud dashboard bu repo-da yoxdur. Onun autentifikasiyalı /v1 contract-a keçidi və response mapping-i labda yoxlanmalıdır.
13. **UID evidence quality:** collector-lar occurrence timestamp və sensor-native identity sahələrini dəyişmədən saxlamalıdır. Upstream itirilmiş timestamp precision və ya qeyri-müəyyən sensor identity backend tərəfindən bərpa edilə bilməz.

REAL_CONNECTOR_ACCEPTANCE.md və POSTGRESQL_ACCEPTANCE.md bu gate-lər üçün command və addımları verir. Secret scan, unit tests və bu release report tam penetration/security audit və ya production certification deyil.

## Phase summary

Faizlər **bu tapşırıq üzrə təxmini engineering-readiness qiymətləndirməsidir**, ölçülmüş test coverage və ya ayrıca təqdim olunmamış tam product roadmap completion deyil. Lokal test acceptance PASS, canlı production acceptance isə açıqdır.

| Phase | Status | Təxmini hazırlıq | Səbəb |
|---|---|---:|---|
| 24 — Unified Backend | PARTIAL | ~90% | API/filter/normalization/dedup/tenant/telemetry/config/deploy dəyişiklikləri test edilib; real PostgreSQL və üç connector gate-i açıqdır. |
| 26 — Incident Engine | PARTIAL | ~90% | Lifecycle, optimistic locking, audit/merge, tenant/mode isolation, Case Pack, immutable Replay və What Changed işləyir; PostgreSQL concurrency/load və real inventory acceptance açıqdır. |
| 27 — Notification Engine | PARTIAL | ~85% | Policy, queue suppression, idempotency, retry/429/5xx və safe payload testləri keçir; PostgreSQL dispatch concurrency və canlı Telegram/SMS/legacy canary gate-ləri açıqdır. |

Fixed source lab integration və gate-ləri keçərək deployment üçün paketlənib; yoxlanılmamış real inteqrasiyaların tamamlandığı iddia edilmir.
