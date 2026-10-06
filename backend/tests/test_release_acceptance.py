"""Final release boundaries; also run unchanged against TEST_DATABASE_URL."""
from pathlib import Path

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Base, Incident, IncidentNote, IncidentAudit, ActionProposal, MergeRequest,
)
from app.ingest import ingest_normalized
from tests.conftest import T0, mk_event


def test_all_tenant_models_have_nonnullable_index_and_scoped_foreign_keys(engine):
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if table.name == "roles":  # global permission vocabulary, not customer data
            continue
        columns = {col["name"]: col for col in inspector.get_columns(table.name)}
        assert columns["tenant_id"]["nullable"] is False, table.name
        assert any("tenant_id" in i["column_names"] for i in inspector.get_indexes(table.name)), table.name
        for fk in inspector.get_foreign_keys(table.name):
            assert "tenant_id" in fk["constrained_columns"], (table.name, fk)
            assert "tenant_id" in fk["referred_columns"], (table.name, fk)
    for table in ("external_refs", "incident_candidates", "incident_events"):
        for fk in inspector.get_foreign_keys(table):
            assert "execution_mode" in fk["constrained_columns"], (table, fk)


@pytest.mark.parametrize("child", ["note", "audit", "proposal", "merge_request", "merged_into"])
def test_all_incident_child_foreign_keys_reject_cross_tenant(engine, settings, child):
    with Session(engine, info={"tenant_id": "A"}) as a:
        ingest_normalized(a, [mk_event("parent")], settings)
        a.commit()
        iid = a.scalar(select(Incident.id))
    with Session(engine, info={"tenant_id": "B"}) as b:
        objects = {
            "note": IncidentNote(incident_id=iid, actor="test", body="context"),
            "audit": IncidentAudit(incident_id=iid, actor="test", action="test"),
            "proposal": ActionProposal(incident_id=iid, proposed_by="test", action_type="test", target="host", expires_at=T0),
            "merge_request": MergeRequest(source_id=iid, target_id=iid, requested_by="test"),
            "merged_into": Incident(opened_at=T0, last_seen=T0, priority="high", title="test", merged_into=iid),
        }
        b.add(objects[child])
        with pytest.raises(IntegrityError):
            b.flush()
        b.rollback()


def test_merge_foreign_key_rejects_cross_mode(session, settings):
    ingest_normalized(session, [mk_event("real")], settings)
    iid = session.scalar(select(Incident.id))
    session.add(Incident(opened_at=T0, last_seen=T0, priority="high", title="test",
                         execution_mode="TEST", merged_into=iid))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_deployment_static_safety_contract():
    root = Path(__file__).resolve().parents[1]
    assert "USER sentinelzone" in (root / "Dockerfile").read_text()
    exclusions = (root / ".dockerignore").read_text().splitlines()
    assert {".env", ".env.*", "*.key", "*.pem"} <= set(exclusions)
    compose = (root / "docker-compose.yml").read_text()
    assert '127.0.0.1:8003:8003' in compose
    assert 'no-new-privileges:true' in compose
    for service in ("backend", "ingest", "dispatch"):
        content = (root / f"deploy/sentinelzone-{service}.service").read_text()
        assert "User=sentinelzone" in content and "NoNewPrivileges=true" in content


@pytest.mark.parametrize("url", ["", "sqlite:///example_test", "postgresql://localhost/production", "postgresql://localhost/test_production"])
def test_postgres_acceptance_refuses_unsafe_target(url):
    from scripts.acceptance import validate_test_url
    with pytest.raises(ValueError):
        validate_test_url(url)


def test_postgres_acceptance_refuses_same_database():
    from scripts.acceptance import validate_test_url
    with pytest.raises(ValueError, match="must not identify"):
        validate_test_url("postgresql://localhost/lab_test", "postgresql://localhost/lab_test")
    assert validate_test_url("postgresql://localhost/lab_test").drivername == "postgresql+psycopg"


def test_acceptance_never_labels_skipped_or_missing_checks_pass():
    import xml.etree.ElementTree as ET
    from scripts.acceptance import classify
    case = ET.fromstring('<testcase name="boundary"><skipped message="no PostgreSQL"/></testcase>')
    assert classify([case], "boundary") == "PARTIAL"
    assert classify([case], "unavailable") == "UNVERIFIED"
    assert classify([ET.fromstring('<testcase name="boundary"><failure/></testcase>')], "boundary") == "FAIL"
