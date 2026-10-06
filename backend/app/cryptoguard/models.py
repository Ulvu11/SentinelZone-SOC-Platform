from datetime import datetime
from sqlalchemy import Boolean, ForeignKeyConstraint, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models import Base, TenantScoped, utcnow
from app.db.types import UTCDateTime

class CryptoGuardAgent(TenantScoped, Base):
    __tablename__ = 'cryptoguard_agents'
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True, default='lab', server_default='lab', index=True)
    agent_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    host_id: Mapped[str] = mapped_column(String(128))
    platform: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    enrolled_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_received_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_observed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

class CryptoGuardEnrollment(TenantScoped, Base):
    __tablename__ = 'cryptoguard_enrollments'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(36))
    platform: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

class CryptoGuardEvent(TenantScoped, Base):
    __tablename__ = 'cryptoguard_events'
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True, default='lab', server_default='lab', index=True)
    agent_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_uid: Mapped[str] = mapped_column(String(36), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(16))
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (
        ForeignKeyConstraint(['tenant_id','agent_id'], ['cryptoguard_agents.tenant_id','cryptoguard_agents.agent_id']),
        UniqueConstraint('tenant_id','agent_id','sequence',name='uq_cg_agent_sequence'),
    )
