import re
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.config import Settings, get_settings
from app.db.models import ActionProposal, ConnectorState, utcnow
from app.db.session import get_db
from app.ingest import ingest_normalized
from tests.conftest import TOKENS, auth, mk_event

ROOT = Path(__file__).resolve().parent.parent


def test_no_lab_ip_hardcoded_in_application_code():
    pat = re.compile(r"\b10\.10\.\d{1,3}\.\d{1,3}\b")
    hits = [str(p) for p in (ROOT / "app").rglob("*.py") if pat.search(p.read_text())]
    assert hits == []  # addresses come from config/env only (fixtures may contain them)


def test_secret_scan_script_passes():
    assert subprocess.run([__import__("sys").executable, "scripts/check_secrets.py"], cwd=ROOT, capture_output=True).returncode == 0


# ---------- 503 when the database is down ----------
class DeadSession:
    info = {}
    def __getattr__(self, name):
        def boom(*a, **k):
            raise OperationalError("select 1", {}, Exception("connection refused"))
        return boom


def test_database_outage_gives_503(client):
    def dead():
        yield DeadSession()

    client.app.dependency_overrides[get_db] = dead
    h = client.get("/health")
    assert h.status_code == 503 and h.json()["status"] == "down"
    assert client.get("/v1/alerts", headers=auth("v")).status_code == 503


# ---------- stale source is never reported healthy ----------
def test_stale_connector_is_degraded_with_cache_age(client, session):
    session.add(ConnectorState(source="splunk", status="healthy", mode="live", last_success_at=utcnow() - timedelta(hours=1)))
    session.commit()
    ov = client.get("/v1/overview", headers=auth("v")).json()
    sp = ov["connectors"]["splunk"]
    assert sp["status"] == "degraded" and sp["cache_age_seconds"] >= 3600 and "stale" in sp["error"]
    assert ov["data_complete"] is False
    assert client.get("/health").json()["connectors"]["splunk"] == "degraded"


# ---------- strictly linear lifecycle ----------
def test_investigating_cannot_skip_to_resolved(client, session, settings):
    ingest_normalized(session, [mk_event("lc1")], settings)
    session.commit()
    assert client.patch("/v1/incidents/1", json={"status": "INVESTIGATING"}, headers={**auth("o"), "If-Match": "1"}).status_code == 200
    assert client.patch("/v1/incidents/1", json={"status": "RESOLVED"}, headers={**auth("o"), "If-Match": "2"}).status_code == 409


# ---------- protected systems really are protected ----------
def _use(client, **kw):
    client.app.dependency_overrides[get_settings] = lambda: Settings(auth_tokens=TOKENS, _env_file=None, **kw)


def test_protected_targets_by_env_and_by_asset_role(client, session, settings):
    ingest_normalized(session, [mk_event("pt1", host="DC01", agent_ip="10.99.9.9"), mk_event("pt2", host="WS05", agent_ip="10.99.9.5")], settings)
    session.commit()
    _use(client, protected_targets="BACKUP01,10.99.0.7")
    body = {"incident_id": "SZ-000001", "action_type": "ISOLATE_ENDPOINT"}
    post = lambda t, who="a": client.post("/v1/action-proposals", json={**body, "target": t}, headers=auth(who))
    assert post("BACKUP01").status_code == 403          # protected by name
    assert post("10.99.0.7").status_code == 403          # protected by IP
    assert post("DC01").status_code == 201               # not protected yet
    # admin marks DC01 as a domain controller -> now protected; non-admin cannot set roles
    assert client.patch("/v1/assets/DC01", json={"role": "domain-controller"}, headers=auth("o")).status_code == 403
    assert client.patch("/v1/assets/DC01", json={"role": "domain-controller"}, headers=auth("ad")).status_code == 200
    assert post("DC01").status_code == 403
    assert post("10.99.9.9").status_code == 403          # same asset addressed by IP
    assert client.patch("/v1/assets/NOPE", json={"role": "x"}, headers=auth("ad")).status_code == 404
    # approving a proposal for a target that became protected later is refused too
    pid = client.get("/v1/action-proposals", headers=auth("v")).json()["items"][0]["proposal_id"]
    assert client.post(f"/v1/action-proposals/{pid}/approve", headers=auth("o")).status_code == 403


def test_proposal_expiry_and_state_machine(client, session, settings):
    ingest_normalized(session, [mk_event("ex1")], settings)
    session.commit()
    r = client.post("/v1/action-proposals", json={"incident_id": "SZ-000001", "action_type": "BLOCK_IP", "target": "203.0.113.5"}, headers=auth("a"))
    pid = r.json()["proposal_id"]
    pr = session.scalars(select(ActionProposal)).one()
    pr.expires_at = utcnow() - timedelta(minutes=1)
    session.commit()
    assert client.get("/v1/action-proposals?status=EXPIRED", headers=auth("v")).json()["items"][0]["proposal_id"] == pid
    assert client.post(f"/v1/action-proposals/{pid}/approve", headers=auth("o")).status_code == 409  # expired
    assert client.post("/v1/action-proposals/ACT-999999/approve", headers=auth("o")).status_code == 404
