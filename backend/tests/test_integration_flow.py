"""End-to-end through the HTTP API only: fixtures -> ingest -> alerts -> incident -> lifecycle -> notifications."""
import pytest

from tests.conftest import auth

pytestmark = pytest.mark.integration


def test_full_soc_flow_over_http(client):
    # 0 data BEFORE any source reported must be 'unknown', not 'all clear'
    first = client.get("/v1/alerts", headers=auth("v")).json()
    assert first["items"] == [] and first["data_complete"] is False

    r = client.post("/v1/admin/ingest/run", headers=auth("ad"))
    assert r.status_code == 200 and r.json()["new"] == 6 and r.json()["incidents_created"] == 1
    assert client.post("/v1/admin/ingest/run", headers=auth("ad")).json()["new"] == 0  # idempotent

    h = client.get("/health").json()
    assert h["status"] == "degraded" and h["database"] == "healthy" and set(h["connectors"].values()) == {"degraded"}

    alerts = client.get("/v1/alerts?limit=100&include_test=true", headers=auth("v")).json()
    assert len(alerts["items"]) == 6 and alerts["data_complete"] is False
    assert {a["original_sensor"] for a in alerts["items"]} == {"wazuh", "suricata", "cowrie", "cryptoguard"}

    ov = client.get("/v1/overview", headers=auth("v")).json()
    assert ov["open_incidents_total"] == 0
    assert client.get("/v1/metrics", headers=auth("v")).json()["events_by_source"] == {}
    ag = client.get("/v1/agents", headers=auth("v")).json()["items"]
    assert ag == []  # TEST fixtures must not alter real asset inventory

    inc = client.get("/v1/incidents?execution_mode=TEST", headers=auth("v")).json()["items"][0]
    assert inc["id"] == "SZ-000001" and inc["host_id"] == "WEB01" and "MULTI_ORIGINAL_SENSOR" in inc["reason_codes"]
    ver = inc["version"]
    op = lambda v: {**auth("o"), "If-Match": str(v)}
    assert client.patch("/v1/incidents/SZ-000001", json={"status": "INVESTIGATING"}, headers=op(ver)).status_code == 200
    assert client.patch("/v1/incidents/SZ-000001", json={"status": "RESOLVED"}, headers=op(ver + 1)).status_code == 409  # must pass CONTAINED
    assert client.post("/v1/incidents/SZ-000001/notes", json={"body": "checked web logs"}, headers=auth("a")).status_code == 201
    kinds = [i["kind"] for i in client.get("/v1/incidents/SZ-000001/timeline", headers=auth("v")).json()["items"]]
    assert {"event", "note", "audit"} <= set(kinds)

    notes = client.get("/v1/notifications", headers=auth("v")).json()["items"]
    assert {n["channel"] for n in notes} == {"dashboard", "telegram"}
    assert {n["status"] for n in notes if n["channel"] == "telegram"} == {"SKIPPED"}  # TELEGRAM_ENABLED=false by default

    assert client.post("/v1/hunts/cowrie-failed-logins/run", headers=auth("o")).json()["rows"]
