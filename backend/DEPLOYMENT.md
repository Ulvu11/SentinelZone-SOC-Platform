# Deployment and hardening

Docker Compose starts PostgreSQL and the backend after database readiness. `alembic upgrade head` runs before Uvicorn. The backend image runs as UID/GID 10001 (sentinelzone); Compose drops capabilities, sets no-new-privileges and a read-only root filesystem, and only publishes 127.0.0.1:8003. Secrets come from runtime .env; .dockerignore excludes secrets/databases/key files.

Fill .env before startup. Compose DATABASE_URL must use host `postgres`, and its password must match POSTGRES_PASSWORD (URL-encode special characters in the URL). POSTGRES_PASSWORD is intentionally empty in the template so Compose refuses to start until it is supplied. Native installation uses the real DB hostname instead.

```bash
docker compose config --quiet
docker compose up -d --build
docker compose exec backend alembic current
docker compose exec backend alembic check
docker compose exec backend python -m app.cli create-user soc-admin admin
```

Do not print `docker compose config` without --quiet into shared reports: it expands secrets. For custom CA files, mount the files read-only and set the corresponding *_CA_FILE path. Do not set verify=false or expose Splunk/Wazuh management ports through the frontend.

`deploy/nginx-sentinelzone.conf` provides TLS 1.2/1.3, a 1 MiB request limit, reverse proxy and basic response headers. Replace hostname/certificate paths. For management/VPN-only access, create `/etc/nginx/snippets/sentinelzone-allowlist.conf` from the supplied example, enter your actual CIDRs and enable the include. Keep `deny all` at the end. Validate with `nginx -t` on the target host before reloading.

Trust only the actual reverse proxy peer via FORWARDED_ALLOW_IPS; for a native loopback proxy it is 127.0.0.1. A host-to-container proxy may appear as the Docker bridge gateway, which must be set explicitly. This affects forwarded scheme/address handling, not upstream connector credentials.

Production validation rejects SQLite/missing DB URL, fixtures, legacy mock routes, debug mode, wildcard CORS with credentials, malformed/short bootstrap tokens, incomplete configured connector credentials, non-HTTPS upstream URLs, and incomplete enabled notification providers. A completely missing connector is allowed to start as not_configured with incomplete data. Database-auth mode does not require static AUTH_TOKENS; bootstrap a DB user via CLI.

Initial integration: keep TELEGRAM_ENABLED=false and SMS_ENABLED=false; validate upstream contracts first. Environment changes require restarting the backend/workers. After restart, dispatch rechecks current channel/legacy/canary policy even for old pending rows. The legacy notifier must separately exclude canary hosts before new delivery is enabled.

`/health` checks database reachability and reports connector degradation in its JSON body. Compose's healthcheck tests database readiness; a green container is not evidence that all sensors are healthy. Inspect `/v1/telemetry-health` and its source timestamps.

Systemd templates remain available in deploy/. Use a dedicated service account and mode-600 EnvironmentFile. Run either scheduler timers or in-process intervals deliberately. PostgreSQL locks protect duplicate ingest/dispatch workers, but provider delivery is at-least-once across a crash after send and before DB commit.

Backend and oneshot worker service templates use non-root users, NoNewPrivileges, PrivateTmp and read-only system/home protections. They target PostgreSQL, not a writable SQLite file under /opt. Run migrations in a maintenance window before starting native systemd services. Docker build/start, systemd execution and nginx -t must still be verified on the target host; this workspace validated their static configuration only.
