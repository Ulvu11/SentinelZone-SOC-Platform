from datetime import datetime,timezone
from unittest.mock import Mock
import asyncio
import os
import pytest
from sqlalchemy import insert,select,text,func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config import Settings
from app.db.models import Event,Incident,IncidentEvent,Notification,ConnectorState,ExternalRef
from app.ingest import ingest_normalized,run_ingest
from app.api.common import connector_states,data_complete
from app.notifications.outbox import dispatch_due
from tests.conftest import mk_event,auth


def test_cross_tenant_foreign_key_is_rejected(engine,settings):
    with Session(engine,info={"tenant_id":"A"}) as a:
        ingest_normalized(a,[mk_event("a")],settings);a.commit()
        iid=a.scalar(select(Incident.id))
    with Session(engine,info={"tenant_id":"B"}) as b:
        b.add(Notification(incident_id=iid,incident_version=1,channel="dashboard",idempotency_key="bad",payload={}))
        with pytest.raises(IntegrityError):b.flush()
        b.rollback()


def test_mode_foreign_key_rejects_mixed_incident_event(session,settings):
    ingest_normalized(session,[mk_event("real"),mk_event("test",is_test=True,prio="low")],settings)
    real=session.scalar(select(Incident).where(Incident.execution_mode=="REAL"))
    session.add(IncidentEvent(incident_id=real.id,event_uid="test",execution_mode="TEST"))
    with pytest.raises(IntegrityError):session.flush()
    session.rollback()


def test_tenant_bulk_insert_rejects_foreign_tenant(session):
    values=mk_event("bad",tenant_id="other").model_dump()
    with pytest.raises(ValueError,match="Cross-tenant"):
        session.execute(insert(Event),[values])


def test_disabled_config_overrides_old_healthy_state(session):
    session.add(ConnectorState(source="splunk",status="healthy",mode="live",last_success_at=datetime.now(timezone.utc)))
    session.flush()
    s=Settings(app_env="production",_env_file=None)
    states=connector_states(session,s)
    assert states["splunk"]["status"]=="not_configured" and data_complete(states) is False


def test_explicit_lab_policy_uses_separate_destination(session,monkeypatch):
    from app.notifications.telegram import SendResult
    s=Settings(telegram_enabled=True,allow_test_notifications=True,test_telegram_chat_id="lab-only",telegram_chat_id="real",_env_file=None)
    ingest_normalized(session,[mk_event("test",is_test=True)],s)
    factory=Mock();factory.return_value.send.return_value=SendResult("success")
    monkeypatch.setattr("app.notifications.telegram.TelegramSender",factory)
    primary=Mock()
    assert dispatch_due(session,s,primary)["sent"]==1
    factory.assert_called_once_with(s.telegram_bot_token,"lab-only")
    assert "TEST" in factory.return_value.send.call_args.args[0]
    primary.send.assert_not_called()


def test_test_incidents_are_hidden_by_default(client,session,settings):
    ingest_normalized(session,[mk_event("test",is_test=True)],settings);session.commit()
    assert client.get("/v1/incidents",headers=auth("v")).json()["items"]==[]
    assert client.get("/v1/incidents?execution_mode=TEST",headers=auth("v")).json()["items"][0]["execution_mode"]=="TEST"


def test_test_notifications_cannot_use_real_destination(session):
    s=Settings(telegram_enabled=True,allow_test_notifications=True,test_telegram_chat_id="lab",telegram_chat_id="real",_env_file=None)
    ingest_normalized(session,[mk_event("lab-event",is_test=True)],s)
    s.test_telegram_chat_id="real"
    sender=Mock()
    assert dispatch_due(session,s,sender)["suppressed"]==1
    sender.send.assert_not_called()


def test_parse_rejections_are_not_healthy(session,settings):
    from app.connectors.base import RawEvent
    class Broken:
        name="splunk";mode="live"
        async def fetch_events(self,since,until):return [RawEvent("wazuh",{})]
    result=asyncio.run(run_ingest(session,settings,[Broken()]))
    assert result["rejected"]==1
    assert connector_states(session,settings)["splunk"]["status"]=="degraded"


@pytest.mark.postgresql
@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL","").startswith("postgresql"),reason="requires PostgreSQL SKIP LOCKED")
def test_postgresql_outbox_skip_locked(engine,settings):
    a,b=Session(engine),Session(engine)
    try:
        ingest_normalized(a,[mk_event("locked")],settings);a.commit()
        a.scalar(select(Notification).where(Notification.channel=="telegram").with_for_update())
        rows=list(b.scalars(select(Notification).where(Notification.channel=="telegram").with_for_update(skip_locked=True)))
        assert rows==[]
    finally:a.rollback();b.rollback();a.close();b.close()
