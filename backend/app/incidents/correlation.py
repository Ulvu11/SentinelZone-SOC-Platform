"""Correlation rules. Same IP alone is NEVER enough; we require same asset + time proximity,
and promote to an incident either on multi-sensor evidence or a single high/critical event.
Port / session context raises the confidence score and adds explainable reason codes."""
from collections import Counter
from datetime import timedelta

from sqlalchemy import select, and_

from app.db.models import Event, Incident, IncidentEvent
from app.normalization.models import PRIORITY_RANK


def rank(p: str) -> int:
    return PRIORITY_RANK.get(p, 0)


def find_open_incident(session, host_id: str, event_time, window: timedelta, execution_mode="REAL") -> Incident | None:
    q = select(Incident).where(Incident.host_id == host_id, Incident.status.notin_(["RESOLVED", "CLOSED"]), Incident.execution_mode == execution_mode).order_by(Incident.last_seen.desc())
    for inc in session.scalars(q):
        if inc.opened_at - window <= event_time <= inc.last_seen + window:
            return inc
    return None


def unlinked_pool(session, row: Event, window: timedelta) -> list[Event]:
    """Other unlinked, medium+ events for the same asset inside the time window."""
    q = (
        select(Event)
        .outerjoin(IncidentEvent, event_link())
        .where(
            IncidentEvent.id.is_(None),
            Event.host_id == row.host_id,
            Event.execution_mode == row.execution_mode,
            Event.event_type != "telemetry",
            Event.event_uid != row.event_uid,
            Event.event_time >= row.event_time - window,
            Event.event_time <= row.event_time + window,
        )
    )
    return [e for e in session.scalars(q) if rank(e.normalized_priority) >= 1]


def incident_events(session, incident_id: int) -> list[Event]:
    q = select(Event).join(IncidentEvent, event_link()).where(IncidentEvent.incident_id == incident_id)
    return list(session.scalars(q))


def sensors_of(session, incident_id: int) -> set[str]:
    return {e.original_sensor for e in incident_events(session, incident_id)}


def analyze(events: list[Event]) -> tuple[set[str], int]:
    """Return (reason_codes, confidence 0..100) for a set of events on ONE asset."""
    codes = {"SAME_ASSET", "WITHIN_TIME_WINDOW"}
    sensors = {e.original_sensor for e in events}
    score = 40
    if len(sensors) > 1:
        codes.add("MULTI_ORIGINAL_SENSOR")
        score += 30
    sessions = Counter(e.session_id for e in events if e.session_id)
    ports = Counter(e.dst_port for e in events if e.dst_port)
    if any(c >= 2 for c in sessions.values()):
        codes.add("SAME_SESSION")
        score += 15
    if any(c >= 2 for c in ports.values()):
        codes.add("SAME_PORT_CONTEXT")
        score += 10
    if len(sensors) == 1 and max((rank(e.normalized_priority) for e in events), default=0) >= 2 and len(events) == 1:
        codes = {"SINGLE_HIGH_PRIORITY_EVENT"}
        score = 50
    return codes, min(score, 100)


def event_link():
    return and_(IncidentEvent.tenant_id == Event.tenant_id, IncidentEvent.execution_mode == Event.execution_mode,
                IncidentEvent.event_uid == Event.event_uid)
