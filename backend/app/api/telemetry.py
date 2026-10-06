from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, AwareDatetime,Field
from sqlalchemy import func,select
from app.api.common import connector_states,data_complete
from app.api.time_filters import time_range,within
from app.auth.permissions import require
from app.config import get_settings
from app.db.models import Asset, Event, Incident, Notification, IncidentEvent
from app.db.session import get_db
from app.incidents.correlation import event_link
from app.services.telemetry import sensor_states,record_telemetry

router=APIRouter(prefix="/v1",tags=["telemetry"])


@router.get("/metrics")
def metrics(agent_id: str | None=None,exclude_telemetry: bool=False,times=Depends(time_range),db=Depends(get_db),_=Depends(require("read")),settings=Depends(get_settings)):
    eq=within(select(Event).where(Event.execution_mode=="REAL"),Event.event_time,times)
    if exclude_telemetry:
        eq=eq.where(Event.event_type!="telemetry")
    if agent_id:
        eq=eq.where(Event.agent_id==agent_id)
    events=eq.subquery()
    def ec(col):
        return dict(db.execute(select(col,func.count()).group_by(col)).all())
    iq=within(select(Incident).where(Incident.execution_mode=="REAL"),Incident.opened_at,times)
    aq=within(select(Asset),Asset.last_seen,times)
    if agent_id:
        incident_ids=select(IncidentEvent.incident_id).join(Event,event_link()).where(Event.agent_id==agent_id,Event.execution_mode=="REAL")
        iq=iq.where(Incident.id.in_(incident_ids))
        aq=aq.where(Asset.agent_id==agent_id)
    inc=iq.subquery()
    nq=within(select(Notification).where(Notification.incident_id.in_(select(inc.c.id))),Notification.created_at,times).subquery()
    return {"events_by_source":ec(events.c.source),"events_by_priority":ec(events.c.normalized_priority),
            "incidents_by_status":ec(inc.c.status),"incidents_by_priority":ec(inc.c.priority),
            "notifications_by_status":ec(nq.c.status),"assets_total":db.scalar(select(func.count()).select_from(aq.subquery())),
            "connectors":connector_states(db,settings)}


@router.get("/telemetry-health")
def telemetry_health(db=Depends(get_db),_=Depends(require("read")),settings=Depends(get_settings)):
    conns=connector_states(db,settings)
    sensors=sensor_states(db,settings)
    configured=[v for v in sensors.values() if v["expected_interval"] is not None]
    complete=data_complete(conns) and bool(configured) and all(v["status"]=="healthy" for v in configured)
    return {"connectors":conns,"sensors":sensors,"data_complete":complete,
            "status":"healthy" if complete else "degraded"}


class Heartbeat(BaseModel):
    original_sensor: str=Field(pattern=r"^[A-Za-z0-9_-]{1,32}$")
    observed_at: AwareDatetime
    host_id: str | None=Field(default=None,max_length=128)


@router.post("/telemetry/heartbeat",status_code=202)
def heartbeat(body:Heartbeat,db=Depends(get_db),_=Depends(require("admin")),settings=Depends(get_settings)):
    record_telemetry(db,body.original_sensor,body.observed_at,settings,body.host_id,is_alert=False)
    db.commit()
    return {"accepted":True}
