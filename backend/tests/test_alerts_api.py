import time
from datetime import timedelta

from sqlalchemy import insert

from app.db.models import Event
from tests.conftest import T0, auth


def test_zero_alerts_vs_unavailable(client):
    j = client.get("/v1/alerts", headers=auth("v")).json()
    assert j["items"] == [] and j["data_complete"] is False  # no source has reported yet -> NOT 'all clear'
    assert set(j["sources"].values()) == {"unknown"}


def test_overview_and_metrics_after_load(client, loaded):
    ov = client.get("/v1/overview", headers=auth("v")).json()
    assert ov["events_total"] == 6 and ov["open_incidents_total"] == 1 and ov["data_complete"] is True
    assert client.get("/v1/metrics", headers=auth("v")).json()["assets_total"] >= 2
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["database"] == "healthy"
    assert client.get("/v1/agents", headers=auth("v")).json()["items"]


def test_10k_events_paginate_bounded(client, session):
    rows = [dict(event_uid=f"u{i:05d}", event_time=T0 + timedelta(seconds=i), received_at=T0, source="wazuh", original_sensor="wazuh",
                 collector_path=[], event_type="t", host_id=f"H{i % 50}", severity_system="wazuh", normalized_priority="low",
                 is_test=False) for i in range(10_000)]
    session.execute(insert(Event), rows)
    session.commit()
    t = time.time()
    r = client.get("/v1/alerts?limit=500", headers=auth("v")).json()
    assert len(r["items"]) == 500 and r["next_cursor"]
    seen, cur = set(), None
    for _ in range(3):
        page = client.get("/v1/alerts?limit=100" + (f"&cursor={cur}" if cur else ""), headers=auth("v")).json()
        ids = {i["event_uid"] for i in page["items"]}
        assert len(ids) == 100 and not (ids & seen)  # no overlap between pages
        seen |= ids
        cur = page["next_cursor"]
    assert time.time() - t < 10
    assert client.get("/v1/alerts/u00001", headers=auth("v")).status_code == 200
    assert client.get("/v1/alerts/nope", headers=auth("v")).status_code == 404
