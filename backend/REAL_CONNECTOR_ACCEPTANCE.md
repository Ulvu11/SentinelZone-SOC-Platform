# Real connector acceptance — run in your SentinelZone lab

**Status: not executed against real lab systems.** Automated connector tests use recorded fixture payloads and HTTP mocks. The source ZIP contains no real IP, token or password in application code. Supply all live endpoints/credentials/CA paths through .env.

## 1. Establish the deployment

Complete INSTALL.md or DEPLOYMENT.md, migrate to 0003, create a DB user and keep TELEGRAM_ENABLED=false, SMS_ENABLED=false, ALLOW_TEST_NOTIFICATIONS=false initially. Configure APP_ENV=production, ALLOW_FIXTURES=false, ENABLE_LEGACY_MOCK_ROUTES=false, and your real PostgreSQL URL.

```bash
python -c 'from app.config import get_settings; get_settings().validate_runtime(); print("configuration accepted")'
alembic current
alembic check
python scripts/export_contracts.py --check
curl --fail-with-body http://127.0.0.1:8003/health
```

Acceptance: database healthy, revision 0003, no runtime/mock contract drift. HTTP 200 with `status=degraded` is not complete telemetry.

## 2. Configure and verify read-only upstream contracts

Configure URLs, credentials and CA files for the backend host. Use least-privilege read-only upstream identities and valid HTTPS certificates. Start by checking reachability/authentication, then fetch a small read-only window:

```bash
python scripts/connector-acceptance.py
python scripts/connector-acceptance.py --fetch --minutes 15 > connector-acceptance.private.json
```

This script does not ingest into the backend database, dispatch messages, or execute actions. It prints only status/counts/sensor names/latest timestamps. Keep the resulting report private until reviewed.

**Splunk:** verify the configured index and sourcetypes against your actual installation. The built-in search accepts wazuh*, suricata* and cowrie* and normalization recognizes their colon-delimited prefixes (e.g. wazuh:alerts, suricata:eve). Each result must expose sourcetype and JSON `_raw`. Arbitrary sourcetype naming requires adapting the small allowlisted connector mapping/query; do not loosen it to free-form client SPL. Confirm that an empty response means an empty requested window, not a wrong index, missing permission, truncated export or search error.

**Wazuh:** the current connector authenticates through `/security/user/authenticate` and checks `/manager/status`, but its configurable WAZUH_ALERTS_PATH is an **alerts-adapter contract**, not a claim that a standard Wazuh Manager exposes `/alerts`. Verify your actual alert provider (commonly an indexer or an adapter/Splunk path). The supported contract is a JSON list, or `items`/`data.affected_items` with `total`/`total_affected_items` for pagination; since/until/limit/offset must have the agreed semantics. A Manager health success does not validate alert retrieval. If using an indexer with a different authentication/query API, adapt the Wazuh connector to that verified contract before enabling it; do not point an incompatible URL at the assumed shape.

**CryptoGuard:** verify `/health` plus configurable CRYPTOGUARD_EVENTS_PATH. Telemetry must contain event_id (or stable payload identity), observed_at, security_risk and host/agent identity as expected by its normalizer. Supported envelopes are a JSON list or `items` plus optional next_cursor. Confirm since/until handling, cursor progression, timestamp precision and any server-side page cap. Unknown shapes/repeated cursors fail closed.

No server-side empty-result API can prove that all telemetry was delivered; compare provider-side counts and latest timestamps independently. The ingest overlap is 120 seconds by default. Longer late arrivals require increasing it or a controlled bounded backfill after inspecting source retention/pagination.

## 3. Ingest and compare the backend (delivery remains disabled)

Load a backend admin token into a local environment variable without saving it in shell history. The example below uses httpx so tokens do not appear in curl process arguments. Set SOC_BASE_URL and, if required, SOC_CA_FILE to your API/TLS endpoint.

```bash
read -rs -p 'Backend admin token: ' SOC_TOKEN; export SOC_TOKEN; printf '\n'
export SOC_BASE_URL='http://127.0.0.1:8003'
python - <<'PY'
import os,httpx,json
base=os.environ['SOC_BASE_URL']
with httpx.Client(base_url=base,headers={'Authorization':'Bearer '+os.environ['SOC_TOKEN']},
                  verify=os.environ.get('SOC_CA_FILE') or True,timeout=120) as c:
    r=c.post('/v1/admin/ingest/run');r.raise_for_status();print('ingest:',r.json())
    for path in ('/health','/v1/overview','/v1/telemetry-health','/v1/alerts?limit=10'):
        r=c.get(path);r.raise_for_status()
        data=r.json()
        if 'items' in data:
            data={k:v for k,v in data.items() if k!='items'} | {'item_count':len(r.json()['items'])}
        print(path,json.dumps(data,default=str))
PY
unset SOC_TOKEN
```

Confirm original_sensor remains wazuh for Wazuh data forwarded through Splunk. Check one known native alert through both collectors: one event occurrence, merged collector_path, two external refs, one logical sensor. Check two separate Suricata occurrences sharing flow/signature: two event UIDs. Re-ingest the same bounded window: no new incident/notification for duplicate occurrences.

## 4. Validate liveness separately from alerts

Define SENSOR_EXPECTED_INTERVALS only for feeds with a real, verified heartbeat/non-alert telemetry cadence. Supply observations through the source feed or the authenticated admin `/v1/telemetry/heartbeat` integration. Do not post artificial timestamps just to make a source green.

Check fresh telemetry with zero alerts: healthy sensor with no new alert. In a controlled test window stop one telemetry feed, keeping Splunk reachable: that sensor must become degraded after its interval and offline after interval × SENSOR_OFFLINE_MULTIPLIER. Verify restoration and affected asset identities. Windows/other sensors need a real heartbeat adapter; merely listing a sensor in configuration does not install one.

## 5. Verify the frontend contract

Inspect the dashboard's actual network requests: use `/v1/overview`, `/v1/alerts`, `/v1/incidents`, `/v1/assets`, with authentication and tenant-correct credentials. `/api/overview`, `/api/incidents`, `/api/endpoints` must return 404 in production. Match response shapes explicitly; this backend ZIP does not contain or update your existing dashboard frontend.

## 6. Delivery and migration acceptance (requires your deliberate enablement)

Only after the above pass, configure a dedicated canary destination/host set and enable the chosen provider. If the old Telegram notifier is active, keep LEGACY_TELEGRAM_ACTIVE=true to suppress new delivery. For a canary cutover, first exclude those hosts in the old notifier, then update/restart the new engine with the intended policy. Verify one controlled real incident, bounded retries, provider response handling and idempotency. Disable/restart the channel while a message is pending and confirm SUPPRESSED without a provider call.

TEST notification policy is separate, defaults off, supports Telegram only and requires TEST_TELEGRAM_CHAT_ID. SMS cannot be used for test delivery. Replay must leave production incidents, notification counts and action state unchanged.

## 7. PostgreSQL release gate

Create a separate disposable test database and run TESTING.md's full PostgreSQL command. Verify advisory locks, SKIP LOCKED, migration upgrade/downgrade, backup/restore and foreign-key isolation. Run `nginx -t` and build/start the Docker image on your target platform. These target-environment checks were not performed in the supplied execution environment.
