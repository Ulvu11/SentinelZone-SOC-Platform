from dataclasses import dataclass
from datetime import timedelta

from app.db.models import Event, Incident, IncidentAudit, IncidentCandidate, IncidentEvent
from app.incidents import correlation as corr
from app.normalization.models import PRIORITY_NAMES


@dataclass
class Outcome:
    incident: Incident | None = None
    created: bool = False
    escalated: bool = False
    attached: bool = False


def snapshot(inc: Incident) -> dict:
    return {
        "status": inc.status, "priority": inc.priority, "owner": inc.owner, "version": inc.version,
        "last_seen": inc.last_seen.isoformat(), "reason_codes": list(inc.reason_codes or []), "confidence": inc.confidence, "execution_mode": inc.execution_mode, "disposition": inc.disposition,
    }


def audit(session, incident_id, actor, action, prev, new):
    session.add(IncidentAudit(incident_id=incident_id, actor=actor, action=action, previous_state=prev, new_state=new))


def _candidate(session, row: Event, reason: str) -> Outcome:
    session.add(IncidentCandidate(event_uid=row.event_uid, execution_mode=row.execution_mode, host_id=row.host_id, reason=reason))
    return Outcome()


def process_event(session, row: Event, window_minutes: int) -> Outcome:
    if not row.host_id:
        return _candidate(session, row, "NO_ASSET_CONTEXT")
    win = timedelta(minutes=window_minutes)
    inc = corr.find_open_incident(session, row.host_id, row.event_time, win, row.execution_mode)
    if inc:
        return _attach(session, inc, row)
    if corr.rank(row.normalized_priority) < 1:
        return _candidate(session, row, "LOW_PRIORITY")
    pool = corr.unlinked_pool(session, row, win) + [row]
    sensors = {e.original_sensor for e in pool}
    if len(sensors) < 2 and corr.rank(row.normalized_priority) < 2:
        return _candidate(session, row, "SINGLE_SENSOR_BELOW_THRESHOLD")
    codes, confidence = corr.analyze(pool)
    top = max(corr.rank(e.normalized_priority) for e in pool)
    if len(sensors) >= 2 and top == 1:
        top = 2
    inc = Incident(
        opened_at=min(e.event_time for e in pool), last_seen=max(e.event_time for e in pool),
        execution_mode=row.execution_mode, summary=row.summary,
        rule_version="1" if window_minutes == 15 else ("2" if window_minutes == 5 else f"1-window-{window_minutes}"), status="NEW", priority=PRIORITY_NAMES[top], version=1, host_id=row.host_id, confidence=confidence,
        title=f"{row.host_id}: {(row.summary or row.event_type)[:150]}", reason_codes=sorted(codes),
    )
    session.add(inc)
    session.flush()
    for e in pool:
        session.add(IncidentEvent(incident_id=inc.id, event_uid=e.event_uid, execution_mode=e.execution_mode))
    session.flush()
    audit(session, inc.id, "system", "INCIDENT_CREATED", None, snapshot(inc))
    return Outcome(incident=inc, created=True)


def _attach(session, inc: Incident, row: Event) -> Outcome:
    prev = snapshot(inc)
    late = row.event_time < inc.last_seen
    session.add(IncidentEvent(incident_id=inc.id, event_uid=row.event_uid, execution_mode=row.execution_mode))
    session.flush()
    events = corr.incident_events(session, inc.id)
    codes, confidence = corr.analyze(events)
    codes |= set(inc.reason_codes or []) - {"SINGLE_HIGH_PRIORITY_EVENT", "MANUAL"} if len(events) > 1 else set()
    sensors = {e.original_sensor for e in events}
    new_rank = max(corr.rank(inc.priority), corr.rank(row.normalized_priority))
    if len(sensors) > 1 and new_rank == 1:
        new_rank = 2
    escalated = new_rank > corr.rank(inc.priority)
    inc.priority = PRIORITY_NAMES[new_rank]
    inc.last_seen = max(inc.last_seen, row.event_time)
    inc.opened_at = min(inc.opened_at, row.event_time)
    inc.reason_codes = sorted(codes)
    inc.confidence = max(confidence, inc.confidence or 0)
    inc.version = inc.version + 1
    session.flush()
    audit(session, inc.id, "system", "LATE_EVENT_ATTACHED" if late else "EVENT_ATTACHED", prev, snapshot(inc))
    return Outcome(incident=inc, escalated=escalated, attached=True)
