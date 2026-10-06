from sqlalchemy import func, select
from sqlalchemy.orm.exc import StaleDataError

from app.db.models import Event, Incident, IncidentAudit, IncidentEvent, IncidentNote, MergeRequest
from app.incidents.correlation import sensors_of
from app.incidents.engine import audit, snapshot
from app.incidents.models import TRANSITIONS, Conflict, NotFound, parse_incident_id
from app.normalization.models import PRIORITY_NAMES
from app.db.models import utcnow
from app.db.tenancy import scoped_get
from app.db.repositories.events import EventRepository
from app.incidents.correlation import event_link


def get_or_404(session, raw_id: str) -> Incident:
    inc = scoped_get(session, Incident, parse_incident_id(raw_id))
    if inc is None:
        raise NotFound(raw_id)
    return inc


def to_out(session, inc: Incident) -> dict:
    count = session.scalar(select(func.count()).select_from(IncidentEvent).where(IncidentEvent.incident_id == inc.id))
    return {
        "id": inc.code, "tenant_id":inc.tenant_id, "execution_mode":inc.execution_mode,
        "summary":inc.summary or inc.title, "disposition":inc.disposition, "updated_at":inc.updated_at,
        "rule_id":inc.rule_id, "rule_version":inc.rule_version, "status": inc.status, "priority": inc.priority, "owner": inc.owner, "version": inc.version,
        "opened_at": inc.opened_at, "last_seen": inc.last_seen, "host_id": inc.host_id, "title": inc.title,
        "reason_codes": list(inc.reason_codes or []), "original_sensors": sorted(sensors_of(session, inc.id)),
        "event_count": count or 0, "confidence": inc.confidence or 0, "merged_into": f"SZ-{inc.merged_into:06d}" if inc.merged_into else None,
    }


def create_manual(session, body, actor: str) -> Incident:
    now = utcnow()
    inc = Incident(opened_at=now, last_seen=now, status="NEW", priority=body.priority, version=1,
                   execution_mode=body.execution_mode, summary=body.summary or body.title, host_id=body.host_id, title=body.title, reason_codes=["MANUAL"])
    session.add(inc)
    session.flush()
    for uid in body.event_uids:
        if EventRepository(session).get(uid, body.execution_mode) is None:
            raise NotFound(f"event {uid}")
        if session.scalar(select(IncidentEvent.id).where(IncidentEvent.event_uid == uid, IncidentEvent.execution_mode == body.execution_mode)):
            raise Conflict(f"event {uid} already belongs to an incident")
        session.add(IncidentEvent(incident_id=inc.id, event_uid=uid, execution_mode=body.execution_mode))
    audit(session, inc.id, actor, "INCIDENT_CREATED_MANUAL", None, snapshot(inc))
    session.commit()
    return inc


def update(session, raw_id: str, expected_version: int, patch, actor: str) -> Incident:
    inc = get_or_404(session, raw_id)
    if inc.version != expected_version:
        raise Conflict("version mismatch", inc.version)
    prev = snapshot(inc)
    if patch.status and patch.status != inc.status:
        if patch.status not in TRANSITIONS[inc.status]:
            raise Conflict(f"invalid transition {inc.status} -> {patch.status}", inc.version)
        inc.status = patch.status
    if patch.status == "CLOSED" and not (patch.disposition or inc.disposition):
        raise Conflict("CLOSED requires disposition", inc.version)
    if patch.summary is not None:
        inc.summary = patch.summary
    if patch.disposition is not None:
        inc.disposition = patch.disposition
    if patch.owner is not None:
        inc.owner = patch.owner
    if patch.priority:
        inc.priority = patch.priority
    inc.version = inc.version + 1
    audit(session, inc.id, actor, "INCIDENT_UPDATED", prev, snapshot(inc))
    try:
        session.commit()
    except StaleDataError:  # concurrent writer won the race
        session.rollback()
        raise Conflict("concurrent modification")
    return inc


def add_note(session, raw_id: str, body: str, actor: str) -> IncidentNote:
    inc = get_or_404(session, raw_id)
    note = IncidentNote(incident_id=inc.id, actor=actor, body=body)
    session.add(note)
    audit(session, inc.id, actor, "NOTE_ADDED", None, {"note_chars": len(body)})
    session.commit()
    return note


def _do_merge(session, raw_id: str, target_raw: str, actor: str) -> Incident:
    src, tgt = get_or_404(session, raw_id), get_or_404(session, target_raw)
    if src.id == tgt.id:
        raise Conflict("cannot merge an incident into itself")
    if src.execution_mode != tgt.execution_mode:
        raise Conflict("Cannot merge REAL and TEST incidents")
    if src.status in ("RESOLVED", "CLOSED") or tgt.status in ("RESOLVED", "CLOSED"):
        raise Conflict("cannot merge resolved incidents")
    ps, pt = snapshot(src), snapshot(tgt)
    session.query(IncidentEvent).filter(IncidentEvent.incident_id == src.id).update({"incident_id": tgt.id})
    tgt.last_seen = max(tgt.last_seen, src.last_seen)
    tgt.opened_at = min(tgt.opened_at, src.opened_at)
    tgt.reason_codes = sorted(set(tgt.reason_codes or []) | set(src.reason_codes or []))
    if PRIORITY_NAMES.index(src.priority) > PRIORITY_NAMES.index(tgt.priority):
        tgt.priority = src.priority
    tgt.version = tgt.version + 1
    src.status, src.merged_into, src.version = "RESOLVED", tgt.id, src.version + 1
    audit(session, src.id, actor, "MERGED_INTO", ps, snapshot(src))
    audit(session, tgt.id, actor, "MERGED_FROM", pt, snapshot(tgt))
    return tgt


def merge(session, raw_id: str, target_raw: str, actor: str) -> Incident:
    """Direct merge: only callable by an operator (the operator IS the approval). Recorded as an APPROVED request."""
    tgt = _do_merge(session, raw_id, target_raw, actor)
    src = get_or_404(session, raw_id)
    session.add(MergeRequest(source_id=src.id, target_id=tgt.id, status="APPROVED", requested_by=actor,
                             decided_by=actor, decided_at=utcnow()))
    session.commit()
    return tgt


def request_merge(session, raw_id: str, target_raw: str, actor: str) -> MergeRequest:
    src, tgt = get_or_404(session, raw_id), get_or_404(session, target_raw)
    if src.id == tgt.id:
        raise Conflict("cannot merge an incident into itself")
    mr = MergeRequest(source_id=src.id, target_id=tgt.id, status="PENDING", requested_by=actor)
    session.add(mr)
    audit(session, src.id, actor, "MERGE_REQUESTED", None, {"target": tgt.code})
    session.commit()
    return mr


def decide_merge(session, mr_id: int, approve: bool, actor: str) -> MergeRequest:
    mr = scoped_get(session, MergeRequest, mr_id)
    if mr is None:
        raise NotFound(f"merge request {mr_id}")
    if mr.status != "PENDING":
        raise Conflict(f"merge request is already {mr.status}")
    if mr.requested_by == actor:
        raise PermissionError("requester cannot decide their own merge request")
    if approve:
        _do_merge(session, f"SZ-{mr.source_id:06d}", f"SZ-{mr.target_id:06d}", actor)
    mr.status, mr.decided_by, mr.decided_at = ("APPROVED" if approve else "REJECTED"), actor, utcnow()
    session.commit()
    return mr


def timeline(session, raw_id: str) -> list[dict]:
    inc = get_or_404(session, raw_id)
    items = []
    q = select(Event).join(IncidentEvent, event_link()).where(IncidentEvent.incident_id == inc.id)
    for e in session.scalars(q):
        items.append({"ts": e.event_time, "kind": "event", "actor": e.original_sensor,
                      "detail": {"event_uid": e.event_uid, "priority": e.normalized_priority, "summary": e.summary}})
    for n in session.scalars(select(IncidentNote).where(IncidentNote.incident_id == inc.id)):
        items.append({"ts": n.created_at, "kind": "note", "actor": n.actor, "detail": {"body": n.body}})
    for a in session.scalars(select(IncidentAudit).where(IncidentAudit.incident_id == inc.id)):
        items.append({"ts": a.timestamp, "kind": "audit", "actor": a.actor,
                      "detail": {"action": a.action, "previous": a.previous_state, "new": a.new_state}})
    return sorted(items, key=lambda i: (i["ts"], i["kind"], __import__("json").dumps(i["detail"], sort_keys=True)))
