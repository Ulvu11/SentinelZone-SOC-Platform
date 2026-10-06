from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from app.api.common import connector_states, data_complete
from app.api.time_filters import time_range,within
from app.auth.permissions import require
from app.db.models import Event,Incident
from app.db.session import get_db
from app.config import get_settings

router=APIRouter(prefix="/v1",tags=["overview"])


@router.get("/overview")
def overview(times=Depends(time_range), db=Depends(get_db), _=Depends(require("read")), settings=Depends(get_settings)):
    states=connector_states(db,settings)
    events=within(select(Event.normalized_priority,func.count()).where(Event.execution_mode=="REAL"), Event.event_time,times)
    incidents=within(select(Incident.priority,func.count()).where(Incident.execution_mode=="REAL",Incident.status.notin_(["RESOLVED","CLOSED"])),Incident.opened_at,times)
    by_prio=dict(db.execute(events.group_by(Event.normalized_priority)).all())
    open_inc=dict(db.execute(incidents.group_by(Incident.priority)).all())
    return {"generated_at":datetime.now(timezone.utc),"events_total":sum(by_prio.values()),"events_by_priority":by_prio,
            "open_incidents_by_priority":open_inc,"open_incidents_total":sum(open_inc.values()),
            "connectors":states,"data_complete":data_complete(states)}
