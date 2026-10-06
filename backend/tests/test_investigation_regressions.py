from datetime import datetime,timezone
from unittest.mock import Mock
import json
import secrets
import pytest
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session
from app.db.models import Event,Incident,IncidentEvent,ExternalRef,Notification,Asset,EventSet,ReplayRun,ActionProposal,AssetSnapshot
from app.db.tenancy import scoped_get
from app.ingest import ingest_normalized
from app.config import get_settings,Settings
from app.incidents import replay
from app.services.what_changed import compare_states
from tests.conftest import mk_event,auth


def populate(engine,tenant,priority="high",uid="shared",sensor="wazuh"):
    with Session(engine,info={"tenant_id":tenant}) as s:
        ev=mk_event(uid,host="SAME-HOST",prio=priority,sensor=sensor,evidence_ref=f"{tenant}:ref",agent_id="AGENT")
        ingest_normalized(s,[ev],Settings(_env_file=None));s.commit()
        inc=s.scalar(select(Incident))
        return inc.id if inc else None


def tenant_auth(client,settings):
    a, b = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    settings.auth_tokens += f";{a}:alice:admin:A;{b}:bob:admin:B"
    client.app.dependency_overrides[get_settings]=lambda:settings
    return {"Authorization":f"Bearer {a}"},{"Authorization":f"Bearer {b}"}


def test_cross_tenant_events_do_not_correlate(engine):
    populate(engine,"A","medium",sensor="wazuh")
    populate(engine,"B","medium",sensor="suricata")
    for tenant in ("A","B"):
        with Session(engine,info={"tenant_id":tenant}) as s:
            assert s.scalar(select(func.count()).select_from(Event))==1
            assert s.scalar(select(func.count()).select_from(Incident))==0


def test_cross_tenant_incident_access_denied(client,engine,settings):
    ia=populate(engine,"A");ib=populate(engine,"B")
    ha,hb=tenant_auth(client,settings)
    assert client.get(f"/v1/incidents/{ia}",headers=ha).status_code==200
    for suffix in ("","/timeline","/case-pack"):
        assert client.get(f"/v1/incidents/{ia}{suffix}",headers=hb).status_code==404
    assert client.patch(f"/v1/incidents/{ia}",headers={**hb,"If-Match":"1"},json={"owner":"stolen"}).status_code==404
    assert client.post(f"/v1/incidents/{ib}/merge",headers=hb,json={"target_id":str(ia)}).status_code==404
    for h,expected in ((ha,ia),(hb,ib),(ha,ia)):
        items=client.get("/v1/incidents",headers=h).json()["items"]
        assert [i["id"] for i in items]==[f"SZ-{expected:06d}"]


def test_external_ref_tenant_scope(client,engine,settings):
    populate(engine,"A");populate(engine,"B")
    ha,hb=tenant_auth(client,settings)
    for h,tenant in ((ha,"A"),(hb,"B")):
        e=client.get("/v1/alerts/shared",headers=h).json()
        assert e["tenant_id"]==tenant and [r["ref"] for r in e["external_refs"]]==[f"{tenant}:ref"]


def test_notifications_tenant_scope(client,engine,settings):
    populate(engine,"A");populate(engine,"B")
    ha,hb=tenant_auth(client,settings)
    for h,tenant in ((ha,"A"),(hb,"B")):
        items=client.get("/v1/notifications",headers=h).json()["items"]
        assert items and {i["tenant_id"] for i in items}=={tenant}


def test_aggregate_queries_are_tenant_scoped(client,engine,settings):
    populate(engine,"A");populate(engine,"B");populate(engine,"B",uid="other")
    ha,hb=tenant_auth(client,settings)
    for h,count in ((ha,1),(hb,2),(ha,1)):
        assert client.get("/v1/overview",headers=h).json()["events_total"]==count
        assert client.get("/v1/metrics",headers=h).json()["events_by_source"]=={"wazuh":count}
        assert len(client.get("/v1/alerts",headers=h).json()["items"])==count
        assert {i["tenant_id"] for i in client.get("/v1/assets",headers=h).json()["items"]}=={"A" if h==ha else "B"}


def test_cross_tenant_write_rejected(engine):
    with Session(engine,info={"tenant_id":"A"}) as s:
        with pytest.raises(ValueError,match="Cross-tenant"):
            ingest_normalized(s,[mk_event("bad",tenant_id="B")],Settings(_env_file=None))


def test_other_tenant_cannot_poll_or_hunt_shared_connector(client,settings):
    ha,_=tenant_auth(client,settings)
    assert client.post("/v1/admin/ingest/run",headers=ha).status_code==403
    assert client.post("/v1/hunts/cowrie-failed-logins/run",headers=ha).status_code==403


def test_db_user_token_resolves_own_tenant(client,engine,settings):
    from app.auth.users import create_user
    with Session(engine,info={"tenant_id":"A"}) as s:
        token=create_user(s,"same-name","viewer","cli");s.commit()
    populate(engine,"A");populate(engine,"B")
    rows=client.get("/v1/alerts",headers={"Authorization":f"Bearer {token}"}).json()["items"]
    assert {r["tenant_id"] for r in rows}=={"A"}


def test_case_pack_is_deterministic_and_complete(client,session,settings):
    ingest_normalized(session,[mk_event("evidence",evidence_ref="splunk:native-1")],settings);session.commit()
    client.post("/v1/incidents/1/notes",json={"body":"investigation note"},headers=auth("a"))
    a=client.get("/v1/incidents/1/case-pack",headers=auth("v"))
    b=client.get("/v1/incidents/1/case-pack",headers=auth("v"))
    assert a.status_code==200 and a.content==b.content
    p=a.json()
    assert {"incident_id","tenant_id","summary","priority","first_seen","last_seen",
            "affected_assets","affected_users","timeline","evidence_ids","raw_evidence_references",
            "correlation","mitre_mapping","analyst_notes","actions_performed","ai_analysis_references",
            "final_disposition","content_sha256"} <= p.keys()
    from app.incidents.replay import canonical_hash
    assert p["content_sha256"] == canonical_hash({key:value for key,value in p.items() if key!="content_sha256"})
    assert p["evidence_ids"]==["evidence"] and p["tenant_id"]=="lab"
    assert p["raw_evidence_references"][0]["references"][0]["ref"]=="splunk:native-1"
    assert p["analyst_notes"][0]["body"]=="investigation note"
    assert len(p["content_sha256"])==64 and p["actions_performed"]==[]
    assert client.get("/v1/incidents/1/case-pack").status_code==401


def snapshot_set(session,settings):
    ingest_normalized(session,[mk_event("s1",prio="medium",sensor="wazuh"),mk_event("s2",prio="medium",sensor="suricata",minutes=10)],settings)
    return replay.create_event_set(session,["s2","s1"],"REAL","ann")


def test_replay_is_deterministic(session,settings):
    evset=snapshot_set(session,settings)
    a=replay.run_replay(session,evset.id,"asset-correlation","1","2","ann")
    b=replay.run_replay(session,evset.id,"asset-correlation","1","2","ann")
    assert a.old_result==b.old_result and a.new_result==b.new_result
    assert len(a.old_result["incidents"])==1 and a.new_result["incidents"]==[]
    assert a.rule_id=="asset-correlation" and a.event_set_id==evset.id


def test_replay_sends_no_notifications(session,settings,monkeypatch):
    evset=snapshot_set(session,settings)
    before=session.scalar(select(func.count()).select_from(Notification))
    import app.notifications.service as ns
    import app.notifications.outbox as no
    blocked=Mock(side_effect=AssertionError("Replay invoked delivery"))
    monkeypatch.setattr(ns,"enqueue_for_incident",blocked);monkeypatch.setattr(no,"dispatch_due",blocked)
    replay.run_replay(session,evset.id,"asset-correlation","1","2","ann")
    assert session.scalar(select(func.count()).select_from(Notification))==before
    blocked.assert_not_called()


def test_replay_does_not_execute_actions(session,settings,monkeypatch):
    evset=snapshot_set(session,settings)
    before=session.scalar(select(func.count()).select_from(ActionProposal))
    from app.api import action_proposals
    blocked=Mock(side_effect=AssertionError("Replay called action path"))
    monkeypatch.setattr(action_proposals,"propose",blocked);monkeypatch.setattr(action_proposals,"_decide",blocked)
    replay.run_replay(session,evset.id,"asset-correlation","1","2","ann")
    assert session.scalar(select(func.count()).select_from(ActionProposal))==before
    blocked.assert_not_called()


def test_replay_does_not_change_production_incidents(session,settings):
    evset=snapshot_set(session,settings)
    rows=[(i.id,i.version,i.priority,i.status,i.updated_at) for i in session.scalars(select(Incident))]
    replay.run_replay(session,evset.id,"asset-correlation","1","2","ann")
    assert rows==[(i.id,i.version,i.priority,i.status,i.updated_at) for i in session.scalars(select(Incident))]
    with pytest.raises(ValueError,match="isolated replay"):
        ingest_normalized(session,[mk_event("replay",execution_mode="REPLAY")],settings)


def test_replay_snapshot_is_immutable(session,settings):
    evset=snapshot_set(session,settings);session.commit()
    evset.events=[]
    with pytest.raises(ValueError,match="immutable"):session.flush()
    session.rollback()


def test_replay_rejects_tampered_snapshot(session,settings):
    evset=snapshot_set(session,settings)
    # Simulate an integrity failure outside the supported application write paths.
    evset.events[0]["normalized_priority"]="critical"
    with pytest.raises(ValueError,match="integrity"):
        replay.run_replay(session,evset.id,"asset-correlation","1","2","ann")


def test_cross_tenant_replay_set_access_denied(engine,settings):
    with Session(engine,info={"tenant_id":"A"}) as s:
        evset=snapshot_set(s,settings);s.commit();eid=evset.id
    with Session(engine,info={"tenant_id":"B"}) as s:
        with pytest.raises(LookupError):replay.run_replay(s,eid,"asset-correlation","1","2","ann")


def test_replay_api_rbac(client,session,settings):
    ingest_normalized(session,[mk_event("api-replay")],settings);session.commit()
    body={"event_uids":["api-replay"]}
    assert client.post("/v1/event-sets",json=body).status_code==401
    assert client.post("/v1/event-sets",json=body,headers=auth("v")).status_code==403
    r=client.post("/v1/event-sets",json=body,headers=auth("a"))
    assert r.status_code==201
    req={"event_set_id":r.json()["event_set_id"]}
    assert client.post("/v1/replay",json=req,headers=auth("v")).status_code==403
    r=client.post("/v1/replay",json=req,headers=auth("a"));assert r.status_code==201
    assert r.json()["new_result"]["execution_mode"]=="REPLAY"
    assert client.get(f"/v1/replay/{r.json()['id']}",headers=auth("v")).status_code==200
    assert client.post("/v1/replay",json={**req,"new_version":"unknown"},headers=auth("a")).status_code==422


def test_what_changed_all_requested_types():
    before={"local_users":["old"],"telemetry_sources":{"suricata":"healthy"},"criticality":"normal"}
    after={"local_users":["old","new"],"services":["new-service"],"startup_items":["startup"],
           "unsigned_processes":["tool.exe"],"outbound_destinations":["192.0.2.99"],
           "telemetry_sources":{"suricata":"offline"},"criticality":"critical"}
    result=compare_states(before,after)
    assert {x["kind"] for x in result["changes"]}=={"new_local_user","new_service","new_startup_item",
           "new_unsigned_process","new_outbound_destination","telemetry_source_stopped","asset_criticality_changed"}
    assert result["classification"]=="investigation_context" and "malicious" not in json.dumps(result)
    assert compare_states(after,after)["changes"]==[]


def test_what_changed_snapshot_api_and_rbac(client,session,settings):
    ingest_normalized(session,[mk_event("inventory",host="HOST")],settings);session.commit()
    path="/v1/assets/HOST/snapshots"
    assert client.post(path,json={},headers=auth("v")).status_code==403
    assert client.post(path,json={},headers=auth("ad")).status_code==201
    assert client.get("/v1/assets/HOST/what-changed",headers=auth("v")).json()["data_complete"] is False
    assert client.post(path,json={"services":["new-service"]},headers=auth("ad")).status_code==201
    diff=client.get("/v1/assets/HOST/what-changed",headers=auth("v")).json()
    assert diff["data_complete"] and diff["changes"]==[{"kind":"new_service","value":"new-service"}]


def test_closed_requires_disposition_and_is_terminal(client,session,settings):
    ingest_normalized(session,[mk_event("lifecycle")],settings);session.commit()
    for version,status in enumerate(["INVESTIGATING","CONTAINED","RESOLVED"],1):
        assert client.patch("/v1/incidents/1",headers={**auth("o"),"If-Match":str(version)},json={"status":status}).status_code==200
    assert client.patch("/v1/incidents/1",headers={**auth("o"),"If-Match":"4"},json={"status":"CLOSED"}).status_code==409
    r=client.patch("/v1/incidents/1",headers={**auth("o"),"If-Match":"4"},json={"status":"CLOSED","disposition":"benign"})
    assert r.status_code==200 and r.json()["disposition"]=="benign"
    assert client.patch("/v1/incidents/1",headers={**auth("o"),"If-Match":"5"},json={"status":"NEW"}).status_code==409


def test_test_incident_cannot_create_action(client,session,settings):
    ingest_normalized(session,[mk_event("test-action",is_test=True)],settings);session.commit()
    assert client.post("/v1/action-proposals",headers=auth("a"),json={"incident_id":"1","action_type":"BLOCK_IP","target":"192.0.2.1"}).status_code==409


def test_telemetry_health_rbac_and_heartbeat(client):
    assert client.get("/v1/telemetry-health").status_code==401
    assert client.get("/v1/telemetry-health",headers=auth("v")).status_code==200
    body={"original_sensor":"windows","observed_at":datetime.now(timezone.utc).isoformat(),"host_id":"WIN"}
    assert client.post("/v1/telemetry/heartbeat",headers=auth("v"),json=body).status_code==403
    assert client.post("/v1/telemetry/heartbeat",headers=auth("ad"),json=body).status_code==202
