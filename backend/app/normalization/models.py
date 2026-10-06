from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

Priority = Literal["low", "medium", "high", "critical"]
PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}
PRIORITY_NAMES = ["low", "medium", "high", "critical"]


class NormalizedEvent(BaseModel):
    """SentinelZone normalized event (see contracts/normalized-event.schema.json).

    Notes: event_time (when it happened) != received_at (when we got it);
    agent_ip (monitored endpoint) != src_ip (network traffic origin);
    original_sensor (who observed) != collector_path (who forwarded it).
    """

    model_config = ConfigDict(from_attributes=True)

    tenant_id: str | None = None
    execution_mode: Literal["REAL", "TEST", "REPLAY"] = "REAL"
    event_uid: str
    event_time: datetime
    received_at: datetime
    source: str
    original_sensor: str
    collector_path: list[str] = []
    event_type: str
    host_id: str | None = None
    agent_id: str | None = None
    agent_ip: str | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    dst_port: int | None = None
    original_severity: str | None = None
    severity_system: str
    normalized_priority: Priority
    is_test: bool = False
    evidence_ref: str | None = None
    summary: str | None = None
    session_id: str | None = None  # network flow / honeypot session (correlation context)

    @model_validator(mode="after")
    def consistent_mode(self):
        if self.execution_mode == "REAL" and self.is_test:
            self.execution_mode = "TEST"
        self.is_test = self.execution_mode == "TEST"
        return self
