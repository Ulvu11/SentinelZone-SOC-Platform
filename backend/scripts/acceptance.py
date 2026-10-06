"""Isolated acceptance. PostgreSQL requires an EMPTY disposable *_test database.

The suite repeatedly drops application tables. Never target a real deployment.
No real connector/provider calls are made; URLs and credentials are not logged.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CATEGORIES = {
    "DB": r"rollback|database_outage|backup_then_restore",
    "MIGRATIONS": r"test_migrations|test_migration_regressions",
    "API": r"test_alerts_api|from_to_filter|metrics_agent_filter|invalid_time_filter|combined_source_time",
    "OPENAPI": r"runtime_openapi_matches",
    "NORMALIZATION": r"test_normalization",
    "SURICATA DEDUP": r"suricata_.*(uid|dropped)",
    "EXTERNAL REFS": r"external_ref|collector_path_preserved",
    "TENANT ISOLATION": r"tenant|foreign_key",
    "TEST/REAL": r"test_event_does_not|test_and_real|test_events_do_not",
    "REPLAY": r"replay",
    "CASE PACK": r"case_pack",
    "WHAT CHANGED": r"what_changed",
    "INCIDENT ENGINE": r"test_incidents|test_idempotency|closed_requires",
    "NOTIFICATIONS": r"test_notifications|queued_notification|notifier_prevents|suppressed_notification",
    "TELEMETRY HEALTH": r"sensor_last_seen|no_alerts_is_not|suricata_can_be_degraded|telemetry_health",
    "RBAC": r"test_rbac|api_rbac",
    "PRODUCTION CONFIG": r"production_(requires|config|no_mock|no_fixture)|missing_production|mock_routes_require",
}


def validate_test_url(raw, production_url=""):
    from sqlalchemy.engine import make_url
    if not raw:
        raise ValueError("TEST_DATABASE_URL is required")
    try:
        url = make_url(raw)
        if url.drivername == "postgresql":
            url = url.set(drivername="postgresql+psycopg")
        if url.drivername != "postgresql+psycopg" or not re.fullmatch(r"[A-Za-z0-9_]+_test", url.database or ""):
            raise ValueError()
    except Exception:
        raise ValueError("Use PostgreSQL/psycopg and a dedicated database ending in _test") from None
    if production_url:
        try:
            other = make_url(production_url)
        except Exception:
            raise ValueError("Invalid DATABASE_URL; unset it for isolated acceptance") from None
        if other.database == url.database:
            raise ValueError("TEST_DATABASE_URL must not identify DATABASE_URL")
    return url


def classify(cases, pattern):
    selected = [c for c in cases if re.search(pattern, c.get("classname", "") + "." + c.get("name", ""))]
    if not selected:
        return "UNVERIFIED"
    if any(c.find("failure") is not None or c.find("error") is not None for c in selected):
        return "FAIL"
    if any(c.find("skipped") is not None for c in selected):
        return "PARTIAL"
    return "PASS"


def migration_probe():
    from alembic import command
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine, inspect, select, text
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session
    from app.db.models import Base, Event, IncidentNote
    from tests.test_migration_regressions import seed_old
    engine = create_engine(os.environ["DATABASE_URL"])
    config = Config(str(ROOT / "alembic.ini"))
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar() == 1
        command.upgrade(config, "0002")
        seed_old(engine)
        seed_old(engine, test=True, uid="legacy-test")
        command.upgrade(config, "head")
        command.check(config)
        with Session(engine) as session:
            modes = dict(session.execute(select(Event.event_uid, Event.execution_mode)).all())
            assert modes == {"legacy": "REAL", "legacy-test": "TEST"}
        with engine.connect() as conn:
            assert MigrationContext.configure(conn).get_current_revision() == "0003"
            if engine.dialect.name == "sqlite":
                assert conn.execute(text("PRAGMA foreign_key_check")).all() == []
        inspector = inspect(engine)
        for table in Base.metadata.sorted_tables:
            if table.name == "roles":
                continue
            assert not next(c for c in inspector.get_columns(table.name) if c["name"] == "tenant_id")["nullable"]
            assert any("tenant_id" in i["column_names"] for i in inspector.get_indexes(table.name))
            for fk in inspector.get_foreign_keys(table.name):
                assert "tenant_id" in fk["constrained_columns"]
        if engine.dialect.name == "postgresql":
            with Session(engine, info={"tenant_id": "other"}) as session:
                session.add(IncidentNote(incident_id=1, actor="acceptance", body="must fail"))
                try:
                    session.flush()
                except IntegrityError:
                    session.rollback()
                else:
                    raise AssertionError("Cross-tenant foreign key was not enforced")
        command.downgrade(config, "0002")
        with engine.connect() as conn:
            assert set(conn.execute(text("SELECT event_uid FROM events")).scalars()) == {"legacy", "legacy-test"}
        command.upgrade(config, "head")
        command.check(config)
        print("MIGRATION HEAD = 0003; populated upgrade/downgrade/upgrade, keys and schema parity PASS")
        # Only tables created in this explicitly disposable acceptance DB.
        command.downgrade(config, "base")
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres", action="store_true")
    parser.add_argument("--allow-test-db-reset", action="store_true")
    parser.add_argument("--migration-probe", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.migration_probe:
        if os.environ.get("SZ_ACCEPTANCE_CHILD") != "1":
            parser.error("Internal probe must be launched by guarded acceptance")
        migration_probe()
        return 0
    if (ROOT / ".env").exists():
        parser.error("Run acceptance in a clean source checkout without a production .env")
    from app.config import Settings
    from sqlalchemy import create_engine, inspect
    test_url = None
    if args.postgres:
        if not args.allow_test_db_reset:
            parser.error("Disposable DB acknowledgement required: --allow-test-db-reset")
        try:
            test_url = validate_test_url(os.environ.get("TEST_DATABASE_URL", ""), os.environ.get("DATABASE_URL", ""))
        except ValueError as exc:
            parser.error(str(exc))
        engine = create_engine(test_url, connect_args={"connect_timeout": 10})
        try:
            if inspect(engine).get_table_names():
                parser.error("Test DB is not empty. Supply a NEW empty *_test database; nothing was changed.")
        finally:
            engine.dispose()
    prefix = "postgresql" if args.postgres else "acceptance"
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    env = dict(os.environ)
    for key in list(env):
        if key.lower() in Settings.model_fields or key.startswith("PYTEST_") or key == "TEST_DATABASE_URL":
            env.pop(key)
    env.update(APP_ENV="test", DEFAULT_TENANT_ID="lab", PYTHONPATH=str(ROOT),
               PYTHONDONTWRITEBYTECODE="1", SZ_ACCEPTANCE_CHILD="1")
    outputs = []

    def run(*arguments, cwd):
        result = subprocess.run([sys.executable, *arguments], cwd=cwd, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output = result.stdout
        if test_url:
            for secret in (test_url.render_as_string(hide_password=False), test_url.password):
                if secret:
                    output = output.replace(secret, "[REDACTED]")
        print(output, end="", flush=True)
        outputs.append(output)
        return result.returncode

    with tempfile.TemporaryDirectory(prefix="sentinelzone-acceptance-") as temporary:
        env["DATABASE_URL"] = test_url.render_as_string(hide_password=False) if test_url else f"sqlite:///{temporary}/acceptance.db"
        if test_url:
            env["TEST_DATABASE_URL"] = env["DATABASE_URL"]
        commands = [
            ("DEPENDENCIES", ("-m", "pip", "check")),
            ("CONTRACTS", (str(ROOT / "scripts/export_contracts.py"), "--check")),
            ("SECRETS", (str(ROOT / "scripts/check_secrets.py"),)),
            ("RUNTIME HTTP", (str(ROOT / "scripts/runtime-smoke.py"),)),
            ("MIGRATION PROBE", (str(Path(__file__).resolve()), "--migration-probe")),
        ]
        preflight = {}
        for label, arguments in commands:
            preflight[label] = "PASS" if run(*arguments, cwd=temporary) == 0 else "FAIL"
            if preflight[label] == "FAIL":
                (reports / f"{prefix}.log").write_text("\n".join(outputs))
                print(f"{label} FAIL; remaining checks UNVERIFIED")
                return 1
        xml = reports / f"{prefix}-tests.xml"
        code = run("-m", "pytest", str(ROOT / "tests"), "-c", str(ROOT / "pytest.ini"),
                   "-q", "-ra", f"--junitxml={xml}", cwd=temporary)
    if not xml.exists():
        print("SUITE FAIL: no JUnit result")
        return 1
    cases = list(ET.parse(xml).iter("testcase"))
    failed = sum(c.find("failure") is not None or c.find("error") is not None for c in cases)
    skipped = sum(c.find("skipped") is not None for c in cases)
    summary = {label: classify(cases, pattern) for label, pattern in CATEGORIES.items()}
    summary.update(preflight)
    counts = {"passed": len(cases) - failed - skipped, "failed": failed, "skipped": skipped}
    pg_status = "UNVERIFIED" if not args.postgres else ("PASS" if code == 0 and not skipped else "PARTIAL" if not code else "FAIL")
    for label, status in summary.items():
        print(f"{label:22} {status}")
    print("POSTGRESQL LIVE ACCEPTANCE =", pg_status)
    for label, count in counts.items():
        print(f"{label} = {count}")
    result = {"database": "postgresql" if args.postgres else "sqlite", "counts": counts,
              "categories": summary, "postgresql_live_acceptance": pg_status,
              "skips": [{"test": c.get("name"), "reason": c.find("skipped").get("message")}
                        for c in cases if c.find("skipped") is not None]}
    (reports / f"{prefix}-summary.json").write_text(json.dumps(result, indent=2) + "\n")
    (reports / f"{prefix}.log").write_text("\n".join(outputs) + "\n" + json.dumps(result, indent=2) + "\n")
    return code or (2 if args.postgres and skipped else 0)


if __name__ == "__main__":
    sys.exit(main())
