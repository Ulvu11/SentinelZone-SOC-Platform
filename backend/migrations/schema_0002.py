from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.types import UTCDateTime


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"
    event_uid: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime)
    source: Mapped[str] = mapped_column(String(32), index=True)
    original_sensor: Mapped[str] = mapped_column(String(32))
    collector_path: Mapped[list] = mapped_column(JSON, default=list)
    event_type: Mapped[str] = mapped_column(String(64))
    host_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    src_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dst_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dst_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    severity_system: Mapped[str] = mapped_column(String(32))
    normalized_priority: Mapped[str] = mapped_column(String(16), index=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    __table_args__ = (Index("ix_events_time_uid", "event_time", "event_uid"),)


class Asset(Base):
    __tablename__ = "assets"
    host_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(UTCDateTime)
    last_seen: Mapped[datetime] = mapped_column(UTCDateTime)
    sources: Mapped[list] = mapped_column(JSON, default=list)


class ExternalRef(Base):
    __tablename__ = "external_refs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_uid: Mapped[str] = mapped_column(ForeignKey("events.event_uid"), index=True)
    system: Mapped[str] = mapped_column(String(32))
    ref: Mapped[str] = mapped_column(String(256))


class IncidentCandidate(Base):
    __tablename__ = "incident_candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_uid: Mapped[str] = mapped_column(ForeignKey("events.event_uid"), index=True)
    host_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class ConnectorState(Base):
    __tablename__ = "connector_state"
    source: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="unknown")
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_event_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    watermark: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(String(256), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime)
    last_seen: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(16), default="NEW", index=True)
    priority: Mapped[str] = mapped_column(String(16), index=True)
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    host_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(256))
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    merged_into: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}

    @property
    def code(self) -> str:
        return f"SZ-{self.id:06d}"


class IncidentEvent(Base):
    __tablename__ = "incident_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    event_uid: Mapped[str] = mapped_column(ForeignKey("events.event_uid"), unique=True)
    linked_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class IncidentNote(Base):
    __tablename__ = "incident_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    actor: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    body: Mapped[str] = mapped_column(Text)


class IncidentAudit(Base):
    __tablename__ = "incident_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    previous_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    incident_version: Mapped[int] = mapped_column(Integer)
    channel: Mapped[str] = mapped_column(String(16))
    recipient_key: Mapped[str] = mapped_column(String(64), default="default")
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_try_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(256), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class NotificationAttempt(Base):
    __tablename__ = "notification_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id"), index=True)
    attempted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    outcome: Mapped[str] = mapped_column(String(16))
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(256), nullable=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Role(Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(16), primary_key=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)


class ActionProposal(Base):
    __tablename__ = "action_proposals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(32))
    target: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24), default="PENDING_APPROVAL")
    proposed_by: Mapped[str] = mapped_column(String(64))
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)


class MergeRequest(Base):
    __tablename__ = "merge_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"))
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    requested_by: Mapped[str] = mapped_column(String(64))
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
