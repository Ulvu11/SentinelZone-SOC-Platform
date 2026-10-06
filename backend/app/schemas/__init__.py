from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IncidentOut(BaseModel):
    id: str
    tenant_id: str
    execution_mode: Literal["REAL", "TEST"] = "REAL"
    summary: str | None = None
    disposition: str | None = None
    updated_at: datetime
    rule_id: str = "asset-correlation"
    rule_version: str = "1"
    status: str
    priority: str
    owner: str | None
    version: int
    opened_at: datetime
    last_seen: datetime
    host_id: str | None
    title: str
    reason_codes: list[str]
    original_sensors: list[str]
    event_count: int
    confidence: int = 0
    merged_into: str | None = None


class IncidentCreate(BaseModel):
    execution_mode: Literal["REAL", "TEST"] = "REAL"
    summary: str | None = Field(default=None, max_length=4000)
    title: str = Field(min_length=3, max_length=200)
    host_id: str | None = None
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    event_uids: list[str] = []


class IncidentPatch(BaseModel):
    summary: str | None = Field(default=None, max_length=4000)
    disposition: str | None = Field(default=None, max_length=64)
    status: Literal["NEW", "INVESTIGATING", "CONTAINED", "RESOLVED", "CLOSED"] | None = None
    owner: str | None = None
    priority: Literal["low", "medium", "high", "critical"] | None = None


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class MergeIn(BaseModel):
    target_id: str


class ProposalIn(BaseModel):
    incident_id: str
    action_type: Literal["BLOCK_IP", "DISABLE_USER", "ISOLATE_ENDPOINT"]
    target: str = Field(min_length=1, max_length=128)
    ttl_minutes: int = Field(default=60, ge=1, le=1440)
