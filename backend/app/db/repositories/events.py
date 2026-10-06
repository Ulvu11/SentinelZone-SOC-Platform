import base64
from datetime import datetime
from sqlalchemy import and_, or_, select
from app.db.models import Event, ExternalRef
from app.db.tenancy import tenant_id
from app.normalization.models import NormalizedEvent


class InvalidCursor(ValueError):
    pass


def encode_cursor(e: Event) -> str:
    return base64.urlsafe_b64encode(f"{e.event_time.isoformat()}|{e.event_uid}|{e.execution_mode}".encode()).decode()


def decode_cursor(c: str):
    try:
        bits = base64.urlsafe_b64decode(c.encode()).decode().split("|")
        ts, uid = bits[:2]
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None or not uid:
            raise ValueError
        return dt, uid, bits[2] if len(bits) == 3 else "REAL"
    except Exception as exc:
        raise InvalidCursor("invalid cursor") from exc


class EventRepository:
    def __init__(self, session):
        self.s = session

    def get(self, uid: str, mode="REAL") -> Event | None:
        return self.s.scalar(select(Event).where(Event.event_uid == uid, Event.execution_mode == mode))

    def exists(self, uid: str, mode="REAL") -> bool:
        return self.get(uid, mode) is not None

    def add(self, ev: NormalizedEvent) -> Event:
        data = ev.model_dump(exclude={"tenant_id"})
        row = Event(**data, tenant_id=tenant_id(self.s))
        self.s.add(row)
        self.s.flush()
        self.merge_evidence(row, ev)
        return row

    def merge_evidence(self, row: Event, ev: NormalizedEvent):
        row.collector_path = list(dict.fromkeys([*(row.collector_path or []), *ev.collector_path]))
        if not ev.evidence_ref:
            return
        system = ev.collector_path[-1] if ev.collector_path else ev.original_sensor
        exists = self.s.scalar(select(ExternalRef.id).where(
            ExternalRef.event_uid == ev.event_uid, ExternalRef.execution_mode == ev.execution_mode,
            ExternalRef.system == system, ExternalRef.ref == ev.evidence_ref))
        if exists is None:
            self.s.add(ExternalRef(event_uid=ev.event_uid, execution_mode=ev.execution_mode, system=system, ref=ev.evidence_ref))
            self.s.flush()

    def refs(self, uid: str, mode="REAL") -> list[dict]:
        rows = self.s.scalars(select(ExternalRef).where(ExternalRef.event_uid == uid, ExternalRef.execution_mode == mode)
                              .order_by(ExternalRef.system, ExternalRef.ref))
        return [{"system": r.system, "ref": r.ref} for r in rows]

    def page(self, limit: int, cursor: str | None = None, priority=None, source=None, host_id=None,
             include_test=False, from_time=None, to_time=None, exclude_telemetry=False):
        q = select(Event)
        for column, value in ((Event.normalized_priority, priority), (Event.source, source), (Event.host_id, host_id)):
            if value:
                q = q.where(column == value)
        if not include_test:
            q = q.where(Event.execution_mode == "REAL")
        if exclude_telemetry:
            q = q.where(Event.event_type != "telemetry")
        if from_time:
            q = q.where(Event.event_time >= from_time)
        if to_time:
            q = q.where(Event.event_time < to_time)
        if cursor:
            t, u, m = decode_cursor(cursor)
            q = q.where(or_(Event.event_time < t, and_(Event.event_time == t, Event.event_uid < u),
                            and_(Event.event_time == t, Event.event_uid == u, Event.execution_mode < m)))
        rows = list(self.s.scalars(q.order_by(Event.event_time.desc(), Event.event_uid.desc(), Event.execution_mode.desc()).limit(limit + 1)))
        more = len(rows) > limit
        rows = rows[:limit]
        return rows, (encode_cursor(rows[-1]) if more and rows else None)
