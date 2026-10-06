import asyncio
import os
import secrets

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Incident, MergeRequest, Notification, User
from app.db.repositories.events import EventRepository
from app.ingest import ingest_normalized, try_ingest_lock
from app.notifications.outbox import dispatch_due
from app.notifications.sms import WebhookSmsProvider
from app.scheduler import dispatch_once, ingest_once
from tests.conftest import auth, mk_event

MOCK_SMS_TOKEN = secrets.token_urlsafe(32)

# ---------------- correlation: port / session context ----------------


def test_session_and_port_context_raise_confidence(session, settings):
    evs = [
        mk_event("c1", sensor="suricata", minutes=0, dst_port=443, session_id="flow-1"),
        mk_event("c2", sensor="cowrie", minutes=1, dst_port=443, session_id="flow-1"),
    ]
    ingest_normalized(session, evs, settings)
    inc = session.scalars(select(Incident)).one()
    assert {"SAME_SESSION", "SAME_PORT_CONTEXT", "MULTI_ORIGINAL_SENSOR"} <= set(inc.reason_codes)
    assert inc.confidence == 95


def test_multi_sensor_without_context_has_lower_confidence(session, settings):
    ingest_normalized(session, [mk_event("d1", sensor="wazuh"), mk_event("d2", sensor="suricata", minutes=1)], settings)
    inc = session.scalars(select(Incident)).one()
    assert inc.confidence == 70 and "SAME_SESSION" not in inc.reason_codes


def test_fixture_incident_exposes_confidence(client, loaded):
    r = client.get("/v1/incidents/SZ-000001", headers=auth("v")).json()
    assert r["confidence"] >= 70 and r["id"] == "SZ-000001"


# ---------------- merge approval workflow ----------------


def _two_incidents(session, settings):
    ingest_normalized(session, [mk_event("m1", host="H1"), mk_event("m2", host="H2")], settings)
    session.commit()


def test_analyst_merge_is_only_a_request(client, session, settings):
    _two_incidents(session, settings)
    r = client.post("/v1/incidents/1/merge", json={"target_id": "SZ-000002"}, headers=auth("a"))
    assert r.status_code == 202 and r.json()["status"] == "PENDING"
    assert client.get("/v1/incidents/1", headers=auth("v")).json()["merged_into"] is None  # nothing merged yet
    mid = r.json()["merge_request_id"]
    assert client.post(f"/v1/merge-requests/{mid}/approve", headers=auth("a")).status_code == 403  # analyst cannot approve
    assert client.post("/v1/incidents/1/merge", json={"target_id": "SZ-000002"}, headers=auth("v")).status_code == 403
    ok = client.post(f"/v1/merge-requests/{mid}/approve", headers=auth("o"))
    assert ok.status_code == 200 and ok.json()["status"] == "APPROVED"
    assert client.get("/v1/incidents/1", headers=auth("v")).json()["merged_into"] == "SZ-000002"
    assert client.post(f"/v1/merge-requests/{mid}/approve", headers=auth("o")).status_code == 409  # already decided


def test_reject_and_no_self_approval(client, session, settings):
    _two_incidents(session, settings)
    mid = client.post("/v1/incidents/1/merge", json={"target_id": "SZ-000002"}, headers=auth("a")).json()["merge_request_id"]
    assert client.post(f"/v1/merge-requests/{mid}/reject", headers=auth("o")).json()["status"] == "REJECTED"
    # operator's own request cannot be approved by the same operator -> needs a different operator
    r = client.post("/v1/incidents/2/merge", json={"target_id": "SZ-000001"}, headers=auth("o"))
    assert r.status_code == 200  # direct operator merge is itself the approval, and is recorded
    assert session.scalars(select(MergeRequest).where(MergeRequest.status == "APPROVED")).first().decided_by == "omar"


# ---------------- telegram canary ----------------


def test_canary_limits_telegram_to_chosen_hosts(session):
    s = Settings(telegram_enabled=True, telegram_canary_enabled=True, telegram_canary_hosts="CANARY01", _env_file=None)
    ingest_normalized(session, [mk_event("k1", host="CANARY01"), mk_event("k2", host="OTHER")], s)
    tg = {n.incident_id: n for n in session.scalars(select(Notification).where(Notification.channel == "telegram"))}
    assert sorted(n.status for n in tg.values()) == ["PENDING", "SKIPPED"]
    assert [n.last_error for n in tg.values() if n.status == "SKIPPED"] == ["outside_canary"]


# ---------------- SMS provider ----------------


def sms(handler):
    return WebhookSmsProvider("https://sms.example/send", MOCK_SMS_TOKEN, "+10000000", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_sms_provider_results():
    assert sms(lambda r: httpx.Response(202)).send("x").kind == "success"
    assert sms(lambda r: httpx.Response(429, headers={"Retry-After": "9"})).send("x").retry_after == 9
    assert sms(lambda r: httpx.Response(503)).send("x").kind == "retry"
    assert sms(lambda r: httpx.Response(401)).send("x").kind == "failed"


def test_critical_incident_goes_out_via_sms(session):
    s = Settings(telegram_enabled=True, sms_enabled=True, _env_file=None)
    ingest_normalized(session, [mk_event("s1", prio="critical")], s)
    seen = {}

    def handler(req):
        seen["body"] = req.content.decode()
        return httpx.Response(200)

    from app.notifications.telegram import TelegramSender
    tg = TelegramSender(secrets.token_urlsafe(32), "1", client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": True}))))
    stats = dispatch_due(session, s, tg, sms_sender=sms(handler))
    assert stats["sent"] == 2 and "SZ-000001" in seen["body"] and MOCK_SMS_TOKEN not in seen["body"]


# ---------------- DB users / roles ----------------


def test_admin_creates_user_whose_token_works_and_can_be_disabled(client, session):
    r = client.post("/v1/admin/users", json={"username": "newbie", "role": "analyst"}, headers=auth("ad"))
    assert r.status_code == 201
    tok = r.json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert client.get("/v1/incidents", headers=h).status_code == 200
    assert client.post("/v1/admin/ingest/run", headers=h).status_code == 403  # analyst
    stored = session.scalars(select(User)).one()
    assert stored.token_hash and tok not in stored.token_hash  # only a hash is stored
    assert client.patch("/v1/admin/users/newbie", json={"is_active": False}, headers=auth("ad")).status_code == 200
    assert client.get("/v1/incidents", headers=h).status_code == 401
    assert client.patch("/v1/admin/users/newbie", json={"is_active": True}, headers=auth("ad")).status_code == 200
    new = client.post("/v1/admin/users/newbie/rotate-token", headers=auth("ad")).json()["token"]
    assert client.get("/v1/incidents", headers=h).status_code == 401  # old token dead
    assert client.get("/v1/incidents", headers={"Authorization": f"Bearer {new}"}).status_code == 200


def test_user_admin_validation_and_permissions(client):
    assert client.post("/v1/admin/users", json={"username": "x1x", "role": "god"}, headers=auth("ad")).status_code == 422
    assert client.post("/v1/admin/users", json={"username": "dup", "role": "viewer"}, headers=auth("ad")).status_code == 201
    assert client.post("/v1/admin/users", json={"username": "dup", "role": "viewer"}, headers=auth("ad")).status_code == 409
    assert client.post("/v1/admin/users", json={"username": "zzz", "role": "viewer"}, headers=auth("o")).status_code == 403
    roles = client.get("/v1/admin/roles", headers=auth("ad")).json()["items"]
    assert {r["name"] for r in roles} == {"viewer", "analyst", "operator", "admin"}


# ---------------- repositories / external refs ----------------


def test_external_refs_are_stored(client, loaded, session):
    items = client.get("/v1/alerts?limit=50", headers=auth("v")).json()["items"]
    uid = next(i["event_uid"] for i in items if i["source"] == "wazuh" and i["host_id"] == "WEB01")
    refs = client.get(f"/v1/alerts/{uid}", headers=auth("v")).json()["external_refs"]
    assert refs and refs[0]["ref"].split(":")[0] in {"splunk", "wazuh-manager"}
    assert EventRepository(session).exists(uid)


# ---------------- scheduler / lock ----------------


def test_scheduler_ingest_and_dispatch_once(engine, settings):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    res = asyncio.run(ingest_once(settings, factory))
    assert res["new"] == 6 and res["incidents_created"] == 1
    assert asyncio.run(ingest_once(settings, factory))["new"] == 0
    assert dispatch_once(settings, factory) == {"sent": 0, "retry": 0, "failed": 0, "suppressed": 0}


@pytest.mark.postgresql
@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql"), reason="advisory lock is PostgreSQL-only")
def test_ingest_lock_blocks_second_worker(engine):
    f = sessionmaker(bind=engine)
    a, b = f(), f()
    try:
        assert try_ingest_lock(a) is True
        assert try_ingest_lock(b) is False  # second worker is refused while first holds the lock
        a.rollback()
        assert try_ingest_lock(b) is True
    finally:
        a.close(); b.close()
