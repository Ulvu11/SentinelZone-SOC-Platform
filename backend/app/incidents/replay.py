"""Versioned deterministic replay in an isolated in-memory database.

Only immutable event sets and replay results are written to the caller's database.
No ingest orchestrator, notification enqueuer, sender or action executor is called.
Rule v1: original 15-minute window. Rule v2: 5-minute window; same scoring policy.
"""
import hashlib
import json
import uuid
import re
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.models import Base, Event, Incident, EventSet, ReplayRun
from app.db.tenancy import scoped_get, tenant_id
from app.normalization.models import NormalizedEvent
from app.incidents.engine import process_event
from app.incidents.correlation import incident_events

RULES = {"asset-correlation": {"1": {"window_minutes":15}, "2": {"window_minutes":5}}}


def canonical_hash(events):
    return hashlib.sha256(json.dumps(events,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def create_event_set(db, event_uids, mode, actor):
    uids=sorted(set(event_uids))
    events=list(db.scalars(select(Event).where(Event.event_uid.in_(uids),Event.execution_mode==mode).order_by(Event.event_time,Event.event_uid)))
    if not uids or len(events)!=len(uids):
        raise LookupError("One or more events were not found in this tenant/mode")
    content=[NormalizedEvent.model_validate(e).model_dump(mode="json") for e in events]
    row=EventSet(id=str(uuid.uuid4()),content_hash=canonical_hash(content),events=content,created_by=actor)
    db.add(row);db.flush()
    return row


def evaluate(events,rule_id,version):
    try:
        rule=RULES[rule_id][version]
    except KeyError:
        custom = re.fullmatch(r"1-window-([0-9]+)", version)
        if rule_id == "asset-correlation" and custom and 1 <= int(custom.group(1)) <= 1440:
            rule = {"window_minutes":int(custom.group(1))}
        else:
            raise ValueError("Unknown rule ID/version") from None
    sandbox=create_engine("sqlite://")
    Base.metadata.create_all(sandbox)
    try:
        tid=events[0]["tenant_id"] if events else "lab"
        with Session(sandbox,info={"tenant_id":tid}) as work:
            for item in sorted(events,key=lambda e:(e["event_time"],e["event_uid"],e["execution_mode"])):
                ev=NormalizedEvent.model_validate(item)
                row=Event(**ev.model_dump())
                work.add(row);work.flush()
                if ev.event_type != "telemetry":
                    process_event(work,row,rule["window_minutes"])
            result=[]
            for inc in work.scalars(select(Incident).order_by(Incident.opened_at,Incident.id)):
                result.append({"host_id":inc.host_id,"input_mode":inc.execution_mode,"priority":inc.priority,
                    "first_seen":inc.opened_at.isoformat(),"last_seen":inc.last_seen.isoformat(),
                    "confidence":inc.confidence,"reason_codes":sorted(inc.reason_codes),
                    "event_uids":sorted(e.event_uid for e in incident_events(work,inc.id))})
            return {"execution_mode":"REPLAY","rule_id":rule_id,"rule_version":version,
                    "incidents":result,"notifications_sent":0,"actions_executed":0}
    finally:
        sandbox.dispose()


def run_replay(db,event_set_id,rule_id,old_version,new_version,actor):
    event_set=scoped_get(db,EventSet,event_set_id)
    if event_set is None:
        raise LookupError("Event set not found")
    if canonical_hash(event_set.events)!=event_set.content_hash:
        raise ValueError("Immutable event set integrity check failed")
    old=evaluate(event_set.events,rule_id,old_version)
    new=evaluate(event_set.events,rule_id,new_version)
    row=ReplayRun(rule_id=rule_id,old_version=old_version,new_version=new_version,event_set_id=event_set.id,
                  old_result=old,new_result=new,actor=actor)
    db.add(row);db.flush()
    return row
