from sqlalchemy import func, select

from app.db.models import Event, Incident, IncidentAudit, IncidentEvent
from app.ingest import ingest_normalized
from tests.conftest import auth, mk_event


def test_full_pipeline_creates_explainable_incident(loaded, session):
    incs = list(session.scalars(select(Incident)))
    assert len(incs) == 1  # only WEB01; CLIENT01 (low) and COWRIE01 (single medium) stay candidates
    inc = incs[0]
    assert inc.host_id == "WEB01" and inc.code == "SZ-000001" and inc.priority == "high"
    assert {"SAME_ASSET", "WITHIN_TIME_WINDOW", "MULTI_ORIGINAL_SENSOR"} <= set(inc.reason_codes)
    n = session.scalar(select(func.count()).select_from(IncidentEvent).where(IncidentEvent.incident_id == inc.id))
    assert n == 3  # suricata + wazuh + cryptoguard; wazuh duplicate via splunk collapsed
    assert loaded["duplicates"] >= 1 and loaded["incidents_created"] == 1


def test_unrelated_hosts_make_separate_incidents(session, settings):
    ingest_normalized(session, [mk_event("a1", host="H1"), mk_event("b1", host="H2")], settings)
    session.commit()
    assert session.scalar(select(func.count()).select_from(Incident)) == 2


def test_same_ip_alone_is_not_enough(session, settings):
    evs = [mk_event("c1", host="H1", prio="medium", src_ip="9.9.9.9"), mk_event("c2", host="H2", prio="medium", src_ip="9.9.9.9", minutes=1)]
    ingest_normalized(session, evs, settings)
    assert session.scalar(select(func.count()).select_from(Incident)) == 0


def test_late_arriving_event_updates_incident_and_audits(session, settings):
    ingest_normalized(session, [mk_event("l1", minutes=10), mk_event("l2", sensor="suricata", minutes=12)], settings)
    session.commit()
    inc = session.scalars(select(Incident)).one()
    v = inc.version
    ingest_normalized(session, [mk_event("l3", sensor="cryptoguard", minutes=8)], settings)  # older than last_seen
    session.commit()
    inc = session.scalars(select(Incident)).one()
    assert inc.version == v + 1
    actions = [a.action for a in session.scalars(select(IncidentAudit))]
    assert "LATE_EVENT_ATTACHED" in actions


def test_db_error_halfway_rolls_back_everything(session, settings, monkeypatch):
    import app.ingest as ing

    calls = {"n": 0}
    real = ing.enqueue_for_incident

    def boom(*a, **k):
        calls["n"] += 1
        raise RuntimeError("db exploded")

    monkeypatch.setattr(ing, "enqueue_for_incident", boom)
    try:
        ingest_normalized(session, [mk_event("r1", host="H1"), mk_event("r2", host="H2")], settings)
    except RuntimeError:
        session.rollback()
    assert session.scalar(select(func.count()).select_from(Event)) == 0
    assert session.scalar(select(func.count()).select_from(Incident)) == 0


def test_old_version_conflicts_and_audit_written(client, session, settings):
    ingest_normalized(session, [mk_event("v1")], settings)
    session.commit()
    r = client.patch("/v1/incidents/SZ-000001", json={"owner": "ann"}, headers={**auth("a"), "If-Match": "1"})
    assert r.status_code == 200 and r.json()["version"] == 2
    r = client.patch("/v1/incidents/SZ-000001", json={"owner": "bob"}, headers={**auth("a"), "If-Match": "1"})
    assert r.status_code == 409 and r.json()["detail"]["current_version"] == 2
    assert client.patch("/v1/incidents/SZ-000001", json={"owner": "x"}, headers=auth("a")).status_code == 428


def test_status_lifecycle_and_invalid_transition(client, session, settings):
    ingest_normalized(session, [mk_event("s1")], settings)
    session.commit()
    h = lambda v: {**auth("o"), "If-Match": str(v)}
    assert client.patch("/v1/incidents/1", json={"status": "RESOLVED"}, headers=h(1)).status_code == 409  # NEW -> RESOLVED invalid
    assert client.patch("/v1/incidents/1", json={"status": "INVESTIGATING"}, headers=h(1)).status_code == 200
    assert client.patch("/v1/incidents/1", json={"status": "CONTAINED"}, headers=h(2)).status_code == 200
    tl = client.get("/v1/incidents/1/timeline", headers=auth("v")).json()["items"]
    assert [i["kind"] for i in tl].count("audit") >= 3


def test_notes_and_merge(client, session, settings):
    ingest_normalized(session, [mk_event("m1", host="H1"), mk_event("m2", host="H2")], settings)
    session.commit()
    assert client.post("/v1/incidents/1/notes", json={"body": "looking"}, headers=auth("a")).status_code == 201
    r = client.post("/v1/incidents/1/merge", json={"target_id": "SZ-000002"}, headers=auth("o"))
    assert r.status_code == 200 and r.json()["event_count"] == 2
