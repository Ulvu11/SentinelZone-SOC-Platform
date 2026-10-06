"""Frozen schema for revision 0003. Do not import application models here."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, ForeignKey, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.types import UTCDateTime


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TenantScoped:
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="lab", server_default="lab", index=True)


class Event(TenantScoped, Base):
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True, default="lab", server_default="lab", index=True)
    __tablename__ = "events"
    event_uid: Mapped[str] = mapped_column(String(64), primary_key=True)
    execution_mode: Mapped[str] = mapped_column(String(8), primary_key=True, default="REAL", server_default="REAL")
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
    __table_args__ = (
        Index("ix_events_time_uid", "event_time", "event_uid"),
        CheckConstraint("execution_mode IN ('REAL','TEST')", name="ck_event_mode"),
        CheckConstraint("(execution_mode = 'TEST' AND is_test = true) OR (execution_mode = 'REAL' AND is_test = false)", name="ck_event_test_mode"),
    )


class Asset(TenantScoped, Base):
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True, default="lab", server_default="lab", index=True)
    __tablename__ = "assets"
    host_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    criticality: Mapped[str] = mapped_column(String(16), default="normal", server_default="normal")
    first_seen: Mapped[datetime] = mapped_column(UTCDateTime)
    last_seen: Mapped[datetime] = mapped_column(UTCDateTime)
    sources: Mapped[list] = mapped_column(JSON, default=list)


class ExternalRef(TenantScoped, Base):
    __tablename__ = "external_refs"
    execution_mode: Mapped[str] = mapped_column(String(8), default="REAL", server_default="REAL")
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_uid: Mapped[str] = mapped_column(String(64), index=True)
    system: Mapped[str] = mapped_column(String(32))
    ref: Mapped[str] = mapped_column(String(256))

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "execution_mode", "event_uid"], ["events.tenant_id", "events.execution_mode", "events.event_uid"], name="fk_refs_event"),
        UniqueConstraint("tenant_id", "execution_mode", "event_uid", "system", "ref", name="uq_external_ref"),
    )


class IncidentCandidate(TenantScoped, Base):
    __tablename__ = "incident_candidates"
    execution_mode: Mapped[str] = mapped_column(String(8), default="REAL", server_default="REAL")
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_uid: Mapped[str] = mapped_column(String(64), index=True)
    host_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "execution_mode", "event_uid"], ["events.tenant_id", "events.execution_mode", "events.event_uid"], name="fk_candidates_event"),
    )


class ConnectorState(TenantScoped, Base):
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True, default="lab", server_default="lab", index=True)
    __tablename__ = "connector_state"
    source: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="unknown")
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_event_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    watermark: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(String(256), nullable=True)


class AuditLog(TenantScoped, Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class Incident(TenantScoped, Base):
    __tablename__ = "incidents"
    execution_mode: Mapped[str] = mapped_column(String(8), default="REAL", server_default="REAL")
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime)
    last_seen: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(16), default="NEW", index=True)
    priority: Mapped[str] = mapped_column(String(16), index=True)
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    host_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    disposition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow, server_default="1970-01-01 00:00:00+00:00")
    rule_id: Mapped[str] = mapped_column(String(64), default="asset-correlation", server_default="asset-correlation")
    rule_version: Mapped[str] = mapped_column(String(32), default="1", server_default="1")
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    merged_into: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}

    @property
    def code(self) -> str:
        return f"SZ-{self.id:06d}"

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_incident_tenant_id"),
        UniqueConstraint("tenant_id", "execution_mode", "id", name="uq_incident_tenant_mode"),
        ForeignKeyConstraint(["tenant_id", "execution_mode", "merged_into"], ["incidents.tenant_id", "incidents.execution_mode", "incidents.id"], name="fk_incident_merge_scope"),
        CheckConstraint("execution_mode IN ('REAL','TEST')", name="ck_incident_mode"),
    )


class IncidentEvent(TenantScoped, Base):
    __tablename__ = "incident_events"
    execution_mode: Mapped[str] = mapped_column(String(8), default="REAL", server_default="REAL")
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(Integer, index=True)
    event_uid: Mapped[str] = mapped_column(String(64))
    linked_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "execution_mode", "event_uid"], ["events.tenant_id", "events.execution_mode", "events.event_uid"], name="fk_links_event"),
        ForeignKeyConstraint(["tenant_id", "execution_mode", "incident_id"], ["incidents.tenant_id", "incidents.execution_mode", "incidents.id"], name="fk_links_incident"),
        UniqueConstraint("tenant_id", "execution_mode", "event_uid", name="uq_incident_event"),
    )


class IncidentNote(TenantScoped, Base):
    __tablename__ = "incident_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(Integer, index=True)
    actor: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    body: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "incident_id"], ["incidents.tenant_id", "incidents.id"], name="fk_incidentnote_incident"),
    )


class IncidentAudit(TenantScoped, Base):
    __tablename__ = "incident_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(Integer, index=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    previous_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "incident_id"], ["incidents.tenant_id", "incidents.id"], name="fk_incidentaudit_incident"),
    )


class Notification(TenantScoped, Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(Integer, index=True)
    incident_version: Mapped[int] = mapped_column(Integer)
    channel: Mapped[str] = mapped_column(String(16))
    recipient_key: Mapped[str] = mapped_column(String(64), default="default")
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_try_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(256), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    template_version: Mapped[str] = mapped_column(String(32), default="1", server_default="1")
    suppression_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "incident_id"], ["incidents.tenant_id", "incidents.id"], name="fk_notification_incident"),
        UniqueConstraint("tenant_id", "id", name="uq_notification_tenant_id"),
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_notification_key"),
    )


class NotificationAttempt(TenantScoped, Base):
    __tablename__ = "notification_attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notification_id: Mapped[int] = mapped_column(Integer, index=True)
    attempted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    outcome: Mapped[str] = mapped_column(String(16))
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(256), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "notification_id"], ["notifications.tenant_id", "notifications.id"], name="fk_attempt_notification"),
    )


class User(TenantScoped, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_user_tenant_name"),
    )


class Role(Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(16), primary_key=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)


class ActionProposal(TenantScoped, Base):
    __tablename__ = "action_proposals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(Integer, index=True)
    action_type: Mapped[str] = mapped_column(String(32))
    target: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24), default="PENDING_APPROVAL")
    proposed_by: Mapped[str] = mapped_column(String(64))
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "incident_id"], ["incidents.tenant_id", "incidents.id"], name="fk_actionproposal_incident"),
    )


class MergeRequest(TenantScoped, Base):
    __tablename__ = "merge_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(Integer, index=True)
    target_id: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    requested_by: Mapped[str] = mapped_column(String(64))
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "source_id"], ["incidents.tenant_id", "incidents.id"], name="fk_merge_source"),
        ForeignKeyConstraint(["tenant_id", "target_id"], ["incidents.tenant_id", "incidents.id"], name="fk_merge_target"),
    )


class SensorState(TenantScoped, Base):
    __tablename__ = "sensor_state"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True, default="lab", server_default="lab", index=True)
    original_sensor: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_event_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_telemetry_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    expected_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="unknown")
    affected_assets: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class EventSet(TenantScoped, Base):
    __tablename__ = "event_sets"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    events: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    created_by: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_event_set_tenant"),)


class ReplayRun(TenantScoped, Base):
    __tablename__ = "replay_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String(64))
    old_version: Mapped[str] = mapped_column(String(32))
    new_version: Mapped[str] = mapped_column(String(32))
    event_set_id: Mapped[str] = mapped_column(String(64))
    old_result: Mapped[dict] = mapped_column(JSON)
    new_result: Mapped[dict] = mapped_column(JSON)
    run_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    actor: Mapped[str] = mapped_column(String(64))
    __table_args__ = (ForeignKeyConstraint(["tenant_id", "event_set_id"], ["event_sets.tenant_id", "event_sets.id"], name="fk_replay_set"),)


class AssetSnapshot(TenantScoped, Base):
    __tablename__ = "asset_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    host_id: Mapped[str] = mapped_column(String(128), index=True)
    captured_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    state: Mapped[dict] = mapped_column(JSON)
    actor: Mapped[str] = mapped_column(String(64))
    __table_args__ = (ForeignKeyConstraint(["tenant_id", "host_id"], ["assets.tenant_id", "assets.host_id"], name="fk_snapshot_asset"),)
