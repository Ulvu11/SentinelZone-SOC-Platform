import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

from app.config import Settings
from app.connectors.base import Connector
from app.db.models import Asset, AuditLog, ConnectorState
from app.db.tenancy import scoped_get, tenant_id
from app.services.telemetry import record_telemetry
from app.db.repositories.events import EventRepository
from app.incidents.engine import process_event
from app.normalization.models import NormalizedEvent
from app.normalization.normalizer import normalize
from app.notifications.service import enqueue_for_incident

log = logging.getLogger("sentinelzone.ingest")


@dataclass
class IngestResult:
    received: int = 0
    new: int = 0
    duplicates: int = 0
    rejected: int = 0
    incidents_created: int = 0
    incidents_updated: int = 0
    notifications_enqueued: int = 0

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def try_ingest_lock(session) -> bool:
    """PostgreSQL advisory lock (released at commit/rollback) so two workers never ingest at the same time."""
    if session.get_bind().dialect.name != "postgresql":
        return True
    return bool(session.scalar(text("select pg_try_advisory_xact_lock(727001)")))


def _upsert_asset(session, ev: NormalizedEvent):
    a = scoped_get(session, Asset, ev.host_id)
    if a is None:
        session.add(Asset(host_id=ev.host_id, agent_id=ev.agent_id, agent_ip=ev.agent_ip,
                          first_seen=ev.event_time, last_seen=ev.event_time, sources=[ev.original_sensor]))
        return
    a.last_seen = max(a.last_seen, ev.event_time)
    a.agent_id = ev.agent_id or a.agent_id
    a.agent_ip = ev.agent_ip or a.agent_ip  # agent_ip is only ever taken from agent_ip, never src_ip
    if ev.original_sensor not in (a.sources or []):
        a.sources = [*(a.sources or []), ev.original_sensor]


def ingest_normalized(session, events: list[NormalizedEvent], settings: Settings) -> IngestResult:
    """Atomic w.r.t. the caller's transaction: this function never commits."""
    res = IngestResult(received=len(events))
    repo = EventRepository(session)
    if any(ev.execution_mode == "REPLAY" for ev in events):
        raise ValueError("REPLAY must use the isolated replay service")
    if any(ev.tenant_id not in (None, tenant_id(session)) for ev in events):
        raise ValueError("Cross-tenant ingest denied")
    fresh, seen, duplicates = [], {}, []
    for ev in events:
        key = (ev.event_uid, ev.execution_mode)
        existing = repo.get(*key)
        if key in seen or existing is not None:
            res.duplicates += 1
            duplicates.append(ev)
            continue
        seen[key] = ev
        fresh.append(ev)
    for ev in fresh:
        if ev.host_id and ev.execution_mode == "REAL":
            _upsert_asset(session, ev)
    session.flush()
    for ev in fresh:
        if not ev.host_id and ev.dst_ip:
            batch_hosts = {v.host_id for v in fresh if v.host_id and v.agent_ip == ev.dst_ip and v.execution_mode == ev.execution_mode}
            if len(batch_hosts) == 1:
                ev.host_id = next(iter(batch_hosts))
            elif not batch_hosts and ev.execution_mode == "REAL":
                matches = list(session.scalars(select(Asset).where(Asset.agent_ip == ev.dst_ip).limit(2)))
                if len(matches) == 1:
                    ev.host_id = matches[0].host_id
        if ev.execution_mode == "REAL":
            record_telemetry(session, ev.original_sensor, ev.event_time, settings, ev.host_id, ev.event_type != "telemetry")
    touched: dict[int, bool] = {}
    for ev in sorted(fresh, key=lambda e: (e.event_time, e.event_uid, e.execution_mode)):
        row = repo.add(ev)
        res.new += 1
        if ev.event_type == "telemetry":
            continue
        out = process_event(session, row, settings.correlation_window_minutes)
        if out.incident is None:
            continue
        if out.created:
            res.incidents_created += 1
        elif out.attached:
            touched[out.incident.id] = True
        if out.created or out.escalated:
            res.notifications_enqueued += enqueue_for_incident(session, out.incident, settings)
    for ev in duplicates:
        repo.merge_evidence(repo.get(ev.event_uid, ev.execution_mode), ev)
    res.incidents_updated = len(touched)
    return res


def _set_state(session, name: str, **vals):
    st = scoped_get(session, ConnectorState, name) or ConnectorState(source=name)
    session.add(st)
    for k, v in vals.items():
        setattr(st, k, v)
    return st


async def run_ingest(session, settings: Settings, connectors: list[Connector]) -> dict:
    now = datetime.now(timezone.utc)
    events: list[NormalizedEvent] = []
    rejected = 0
    for c in connectors:
        st = scoped_get(session, ConnectorState, c.name)
        since = st.watermark - timedelta(seconds=settings.ingest_overlap_seconds) if st and st.watermark else None
        if c.mode == "not_configured":
            _set_state(session, c.name, status="not_configured", mode="not_configured", last_attempt_at=now,
                       error="connector URL not configured")
            continue
        try:
            raws = await c.fetch_events(since, now)
            if len(raws) > settings.max_ingest_events:
                raise ValueError("ingest batch limit exceeded")
        except Exception as e:  # a dead source must never crash the backend
            prev_ok = st.last_success_at if st else None
            fresh_enough = prev_ok and now - prev_ok < timedelta(minutes=settings.stale_after_minutes)
            _set_state(session, c.name, status="degraded" if fresh_enough else "unavailable", mode=c.mode,
                       last_attempt_at=now, error=f"connector_failure:{type(e).__name__}")
            continue
        got = []
        rejected_before = rejected
        for r in raws:
            try:
                ev = normalize(r.kind, r.payload, r.collector_path, now)
                if c.mode == "fixture":
                    ev = ev.model_copy(update={"execution_mode": "TEST", "is_test": True})
                got.append(ev)
            except (KeyError, ValueError, TypeError) as e:
                rejected += 1
                session.add(AuditLog(actor="system", action="EVENT_REJECTED", detail={"source": c.name, "kind": r.kind, "error": type(e).__name__}))
        events.extend(got)
        newest = max((e.event_time for e in got), default=None)
        prev_last = st.last_event_at if st else None
        _set_state(session, c.name, status="healthy" if c.mode == "live" and rejected == rejected_before else "degraded", mode=c.mode, last_attempt_at=now, last_success_at=now, error="normalization_rejections" if rejected != rejected_before else None,
                   last_event_at=max([t for t in (newest, prev_last) if t], default=None),
                   watermark=max([t for t in (newest, st.watermark if st else None) if t], default=None))
    res = ingest_normalized(session, events, settings)
    res.rejected += rejected
    return res.as_dict()
