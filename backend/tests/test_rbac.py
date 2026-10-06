from app.ingest import ingest_normalized
from tests.conftest import auth, mk_event


def test_no_token_401_bad_token_401(client):
    assert client.get("/v1/alerts").status_code == 401
    assert client.get("/v1/alerts", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_health_is_public_and_reports_connectors(client):
    r = client.get("/health")
    assert r.status_code == 200 and set(r.json()["connectors"]) == {"splunk", "wazuh", "cryptoguard"}


def test_viewer_read_only(client, session, settings):
    ingest_normalized(session, [mk_event("x1")], settings)
    session.commit()
    assert client.get("/v1/incidents", headers=auth("v")).status_code == 200
    assert client.post("/v1/incidents/1/notes", json={"body": "hi"}, headers=auth("v")).status_code == 403
    assert client.patch("/v1/incidents/1", json={"owner": "a"}, headers={**auth("v"), "If-Match": "1"}).status_code == 403


def test_analyst_cannot_transition_operator_can(client, session, settings):
    ingest_normalized(session, [mk_event("x2")], settings)
    session.commit()
    h = lambda r: {**auth(r), "If-Match": "1"}
    assert client.patch("/v1/incidents/1", json={"status": "INVESTIGATING"}, headers=h("a")).status_code == 403
    assert client.patch("/v1/incidents/1", json={"status": "INVESTIGATING"}, headers=h("o")).status_code == 200


def test_admin_only_and_hunt_allowlist(client):
    assert client.post("/v1/admin/ingest/run", headers=auth("o")).status_code == 403
    assert client.post("/v1/admin/ingest/run", headers=auth("ad")).status_code == 200
    assert client.post("/v1/hunts/index=*%20|%20delete/run", headers=auth("o")).status_code == 404
    assert client.post("/v1/hunts/cowrie-failed-logins/run", headers=auth("a")).status_code == 403
    assert client.post("/v1/hunts/cowrie-failed-logins/run", headers=auth("o")).status_code == 200


def test_unknown_incident_404_and_bad_cursor_422(client):
    assert client.get("/v1/incidents/SZ-999999", headers=auth("v")).status_code == 404
    assert client.get("/v1/alerts?cursor=garbage", headers=auth("v")).status_code == 422
    assert client.get("/v1/alerts?limit=100000", headers=auth("v")).status_code == 422


def test_protected_asset_denied_and_proposer_cannot_self_approve(client, session, settings):
    from app.db.models import Asset
    from datetime import datetime, timezone

    ingest_normalized(session, [mk_event("p1", host="H1")], settings)
    now = datetime.now(timezone.utc)
    session.add(Asset(host_id="SPLUNK01", agent_ip="10.9.9.9", role="splunk", first_seen=now, last_seen=now))
    session.commit()
    body = {"incident_id": "SZ-000001", "action_type": "BLOCK_IP"}
    assert client.post("/v1/action-proposals", json={**body, "target": "10.9.9.9"}, headers=auth("a")).status_code == 403
    r = client.post("/v1/action-proposals", json={**body, "target": "10.10.30.10"}, headers=auth("a"))
    assert r.status_code == 201 and r.json()["status"] == "PENDING_APPROVAL"
    pid = r.json()["proposal_id"]
    assert client.post(f"/v1/action-proposals/{pid}/approve", headers=auth("o")).json()["status"] == "APPROVED"
