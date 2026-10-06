import asyncio
import json
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from app.main import create_app
from app.config import Settings,ProductionConfigError,get_settings
from app.connectors.cryptoguard import build_connectors
from app.db.models import Event,Incident,Notification,ExternalRef,ConnectorState
from app.ingest import ingest_normalized,run_ingest
from app.normalization.normalizer import normalize
from app.notifications.outbox import dispatch_due
from app.api.common import connector_states,data_complete
from tests.conftest import mk_event,auth,T0


def prod(**kw):
    values=dict(app_env="production",database_url="postgresql+psycopg://unused@localhost/sz_test",_env_file=None)
    values.update(kw)
    return Settings(**values)


def test_production_no_mock_routes():
    app=create_app(prod())
    with TestClient(app) as c:
        for path in ("/api/overview","/api/incidents","/api/endpoints","/api/health"):
            assert c.get(path).status_code==404
        assert c.get("/v1/alerts").status_code==401
    assert "/v1/alerts" in app.openapi()["paths"]


def test_mock_routes_require_explicit_development_flag():
    assert "/api/overview" not in create_app(Settings(_env_file=None)).openapi()["paths"]
    assert "/api/overview" in create_app(Settings(app_env="development",enable_legacy_mock_routes=True,_env_file=None)).openapi()["paths"]
    assert "/api/overview" not in create_app(Settings(app_env="test",enable_legacy_mock_routes=True,_env_file=None)).openapi()["paths"]
    with pytest.raises(ProductionConfigError,match="LEGACY"):
        create_app(prod(enable_legacy_mock_routes=True))


@pytest.mark.parametrize("url",["", "sqlite://", "sqlite:///prod.db"])
def test_production_requires_postgresql(url):
    with pytest.raises(ProductionConfigError,match="DATABASE_URL must be PostgreSQL"):
        create_app(prod(database_url=url))


def test_missing_production_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL",raising=False)
    with pytest.raises(ProductionConfigError,match="PostgreSQL"):
        create_app(Settings(app_env="production",_env_file=None))


@pytest.mark.parametrize("kw,match",[
    ({"allow_fixtures":True},"ALLOW_FIXTURES"),({"debug":True},"DEBUG"),
    ({"cors_origins":"*"},"CORS"),({"auth_db_enabled":False},"authentication"),
    ({"auth_tokens":"short:a:admin"},"AUTH_TOKENS"),
    ({"splunk_url":"https://example.invalid"},"credentials"),
    ({"splunk_url":"http://example.invalid","splunk_token":"x"},"HTTPS"),
    ({"telegram_enabled":True},"Telegram"),({"sms_enabled":True},"SMS"),
    ({"telegram_enabled":True,"telegram_bot_token":"CHANGE_ME","telegram_chat_id":"destination"},"Telegram"),
    ({"sms_enabled":True,"sms_webhook_url":"https://example.invalid","sms_webhook_token":"CHANGE_ME","sms_to":"destination"},"SMS"),
    ({"allow_test_notifications":True,"telegram_chat_id":"same","test_telegram_chat_id":"same"},"must differ"),
    ({"wazuh_alerts_path":"https://evil.invalid"},"relative"),
])
def test_production_config_fails_closed(kw,match):
    with pytest.raises(ProductionConfigError,match=match):create_app(prod(**kw))


def test_production_no_fixture_fallback(session,monkeypatch):
    s=prod(allow_fixtures=True)  # even a bypass of startup cannot enable production fixtures
    cs=build_connectors(s)
    for c in cs:
        monkeypatch.setattr(c,"load_fixture_files",Mock(side_effect=AssertionError("fixture read")))
        assert c.mode=="not_configured"
    result=asyncio.run(run_ingest(session,s,cs));session.flush()
    assert result["new"]==0
    states=connector_states(session,s)
    assert {v["status"] for v in states.values()}=={"not_configured"}
    assert data_complete(states) is False
    assert session.scalar(select(func.count()).select_from(Event))==0


@pytest.mark.parametrize("name",["splunk","wazuh","cryptoguard"])
def test_missing_connector_config_not_healthy(name):
    c=next(x for x in build_connectors(prod()) if x.name==name)
    assert asyncio.run(c.health()).status=="not_configured"
    with pytest.raises(Exception,match="not_configured"):asyncio.run(c.fetch_events(None,None))


def test_missing_splunk_config_not_healthy():test_missing_connector_config_not_healthy("splunk")
def test_missing_wazuh_config_not_healthy():test_missing_connector_config_not_healthy("wazuh")
def test_missing_cryptoguard_config_not_healthy():test_missing_connector_config_not_healthy("cryptoguard")


def suricata(ts="2026-10-04T12:28:00Z",**kw):
    p={"timestamp":ts,"flow_id":500,"src_ip":"192.0.2.1","dest_ip":"192.0.2.2","dest_port":443,
       "alert":{"signature_id":1001,"severity":1},"sensor_id":"probe-1"}
    p.update(kw)
    return p


def test_suricata_same_occurrence_different_collectors_same_uid():
    a=normalize("suricata",suricata(),["suricata"])
    b=normalize("suricata",suricata("2026-10-04T16:28:00+04:00",host="collector-2",_index="forwarded"),["suricata","splunk"])
    assert a.event_uid==b.event_uid


def test_suricata_same_flow_same_signature_different_occurrence_different_uid():
    a=normalize("suricata",suricata(),["suricata"])
    b=normalize("suricata",suricata("2026-10-04T12:31:00Z"),["suricata"])
    assert a.event_uid!=b.event_uid


def test_suricata_second_real_alert_not_dropped(session,settings):
    result=ingest_normalized(session,[normalize("suricata",suricata(t),["suricata"]) for t in
                                     ["2026-10-04T12:28:00Z","2026-10-04T12:31:00Z"]],settings)
    assert result.new==2 and result.duplicates==0
    assert session.scalar(select(func.count()).select_from(Event))==2


def test_test_event_does_not_raise_real_incident_priority(session,settings):
    ingest_normalized(session,[mk_event("real",prio="high")],settings)
    inc=session.scalar(select(Incident).where(Incident.execution_mode=="REAL"))
    before=(inc.priority,inc.confidence,inc.version)
    ingest_normalized(session,[mk_event("test",prio="critical",is_test=True,minutes=1)],settings)
    assert (inc.priority,inc.confidence,inc.version)==before


def test_test_event_does_not_create_real_notification(session):
    s=Settings(telegram_enabled=True,sms_enabled=True,_env_file=None)
    ingest_normalized(session,[mk_event("medium",prio="medium"),mk_event("test",prio="critical",is_test=True)],s)
    assert session.scalar(select(func.count()).select_from(Incident).where(Incident.execution_mode=="REAL"))==0
    assert not list(session.scalars(select(Notification).where(Notification.status=="PENDING")))


def test_test_and_real_events_are_isolated(session,settings):
    ingest_normalized(session,[mk_event("same"),mk_event("same",is_test=True)],settings)
    assert session.scalar(select(func.count()).select_from(Event))==2
    incs=list(session.scalars(select(Incident)))
    assert {i.execution_mode for i in incs}=={"REAL","TEST"}


def test_test_events_do_not_touch_real_assets_or_sensor_state(session,settings):
    from app.db.models import Asset,SensorState
    ingest_normalized(session,[mk_event("test",is_test=True)],settings)
    assert session.scalar(select(func.count()).select_from(Asset))==0
    assert session.scalar(select(func.count()).select_from(SensorState))==0


def queued(session):
    s=Settings(telegram_enabled=True,sms_enabled=True,_env_file=None)
    ingest_normalized(session,[mk_event("critical",prio="critical")],s)
    return s


def test_disabled_telegram_suppresses_queued_notification(session):
    s=queued(session);s.telegram_enabled=False
    tg=Mock();sms=Mock();sms.send.return_value=__import__('app.notifications.telegram',fromlist=['SendResult']).SendResult('success')
    dispatch_due(session,s,tg,sms_sender=sms)
    n=session.scalar(select(Notification).where(Notification.channel=="telegram"))
    assert n.status=="SUPPRESSED" and n.suppression_reason=="CHANNEL_DISABLED" and n.attempts==0
    tg.send.assert_not_called()


def test_disabled_sms_suppresses_queued_notification(session):
    s=queued(session);s.sms_enabled=False;s.telegram_enabled=False
    sender=Mock()
    dispatch_due(session,s,sender,sms_sender=sender)
    n=session.scalar(select(Notification).where(Notification.channel=="sms"))
    assert n.status=="SUPPRESSED" and n.suppression_reason=="CHANNEL_DISABLED"
    sender.send.assert_not_called()


def test_legacy_notifier_prevents_new_telegram_dispatch(session):
    s=queued(session);s.legacy_telegram_active=True;s.sms_enabled=False
    sender=Mock();dispatch_due(session,s,sender,sms_sender=sender)
    n=session.scalar(select(Notification).where(Notification.channel=="telegram"))
    assert n.status=="SUPPRESSED" and n.suppression_reason=="LEGACY_NOTIFIER_ACTIVE"
    sender.send.assert_not_called()


def test_suppressed_notification_sender_not_called(session):
    s=queued(session);s.telegram_canary_enabled=True;s.telegram_canary_hosts="OTHER";s.sms_enabled=False
    sender=Mock();stats=dispatch_due(session,s,sender,sms_sender=sender)
    assert stats["suppressed"]==2
    sender.send.assert_not_called()


def test_duplicate_event_merges_external_refs(session,settings):
    from app.db.repositories.events import EventRepository
    a=mk_event("dup",collector_path=["wazuh-manager"],evidence_ref="wazuh:1")
    b=mk_event("dup",collector_path=["wazuh-manager","splunk"],evidence_ref="splunk:2")
    ingest_normalized(session,[a,b],settings)
    assert session.scalar(select(func.count()).select_from(Event))==1
    assert len(EventRepository(session).refs("dup"))==2


def test_duplicate_external_ref_is_idempotent(session,settings):
    a=mk_event("dup",collector_path=["splunk"],evidence_ref="splunk:1")
    ingest_normalized(session,[a,a],settings);ingest_normalized(session,[a],settings)
    assert session.scalar(select(func.count()).select_from(ExternalRef))==1


def test_collector_path_preserved(session,settings):
    from app.db.repositories.events import EventRepository
    a=mk_event("dup",collector_path=["wazuh-manager"],evidence_ref="wazuh:1")
    b=mk_event("dup",collector_path=["wazuh-manager","splunk"],evidence_ref="splunk:2")
    ingest_normalized(session,[a],settings);ingest_normalized(session,[b],settings)
    assert EventRepository(session).get("dup").collector_path==["wazuh-manager","splunk"]


def seed_times(session,settings):
    ingest_normalized(session,[mk_event("old",host="H1",agent_id="A",minutes=0),mk_event("new",host="H2",agent_id="B",minutes=60)],settings)
    session.commit()


def interval():return {"from":(T0+timedelta(minutes=30)).isoformat(),"to":(T0+timedelta(minutes=61)).isoformat()}


def test_alerts_from_to_filter(client,session,settings):
    seed_times(session,settings)
    items=client.get("/v1/alerts",params=interval(),headers=auth("v")).json()["items"]
    assert [e["event_uid"] for e in items]==["new"]


def test_alerts_combined_source_time_cursor_limits(client,session,settings):
    ingest_normalized(session, [
        mk_event("first", minutes=0),
        mk_event("second", minutes=1),
        mk_event("other-source", sensor="suricata", minutes=1),
        mk_event("exclusive-end", minutes=2),
    ], settings)
    session.commit()
    # Equivalent UTC+04 bounds, including exact inclusive start/exclusive end.
    params={"source":"wazuh","from":"2026-10-04T16:00:00+04:00",
            "to":"2026-10-04T16:02:00+04:00","limit":1}
    first=client.get("/v1/alerts",params=params,headers=auth("v")).json()
    assert [e["event_uid"] for e in first["items"]]==["second"]
    second=client.get("/v1/alerts",params={**params,"cursor":first["next_cursor"]},headers=auth("v")).json()
    assert [e["event_uid"] for e in second["items"]]==["first"]
    assert second["next_cursor"] is None


def test_overview_from_to_filter(client,session,settings):
    seed_times(session,settings)
    body=client.get("/v1/overview",params=interval(),headers=auth("v")).json()
    assert body["events_total"]==1 and body["open_incidents_total"]==1


def test_metrics_agent_filter(client,session,settings):
    seed_times(session,settings)
    body=client.get("/v1/metrics",params={"agent_id":"A"},headers=auth("v")).json()
    assert body["events_by_source"]=={"wazuh":1} and body["assets_total"]==1
    none=client.get("/v1/metrics",params={"agent_id":"unknown"},headers=auth("v")).json()
    assert none["events_by_source"]=={} and none["incidents_by_status"]=={} and none["assets_total"]==0


def test_metrics_from_to_filter(client,session,settings):
    seed_times(session,settings)
    body=client.get("/v1/metrics",params=interval(),headers=auth("v")).json()
    assert body["events_by_source"]=={"wazuh":1} and body["incidents_by_status"]=={"NEW":1}


@pytest.mark.parametrize("path",["/v1/alerts","/v1/overview","/v1/metrics"])
@pytest.mark.parametrize("params",[{"from":"bad"},{"to":"2026-01-01T00:00:00"},{"from":"2027-01-01T00:00:00Z","to":"2026-01-01T00:00:00Z"}])
def test_invalid_time_filter_422(client,path,params):
    assert client.get(path,params=params,headers=auth("v")).status_code==422


def test_sensor_last_seen(session,settings):
    from app.services.telemetry import record_telemetry,sensor_states
    now=datetime.now(timezone.utc)
    settings.sensor_expected_intervals='{"suricata":60}'
    record_telemetry(session,"suricata",now,settings,"WEB",is_alert=True)
    item=sensor_states(session,settings,now)["suricata"]
    assert item["last_event_at"]==now and item["affected_assets"]==["WEB"] and item["status"]=="healthy"


def test_no_alerts_is_not_no_telemetry(session,settings):
    from app.services.telemetry import record_telemetry,sensor_states
    now=datetime.now(timezone.utc);settings.sensor_expected_intervals='{"suricata":60}'
    record_telemetry(session,"suricata",now,settings,is_alert=False)
    item=sensor_states(session,settings,now)["suricata"]
    assert item["status"]=="healthy" and item["last_event_at"] is None
    assert session.scalar(select(func.count()).select_from(Event))==0


def test_suricata_can_be_degraded_while_splunk_is_healthy(session,settings):
    from app.services.telemetry import record_telemetry,sensor_states
    now=datetime.now(timezone.utc);settings.sensor_expected_intervals='{"suricata":60}'
    record_telemetry(session,"suricata",now-timedelta(seconds=90),settings)
    session.add(ConnectorState(source="splunk",status="healthy",mode="live",last_success_at=now));session.flush()
    assert connector_states(session,settings)["splunk"]["status"]=="healthy"
    assert sensor_states(session,settings,now)["suricata"]["status"]=="degraded"
    assert sensor_states(session,settings,now+timedelta(minutes=5))["suricata"]["status"]=="offline"


def test_health_200_can_be_degraded(client):
    r=client.get("/health")
    assert r.status_code==200 and r.json()["status"]=="degraded" and r.json()["database"]=="healthy"
