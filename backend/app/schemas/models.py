from typing import Literal
from pydantic import BaseModel

Severity = Literal["critical", "high", "medium", "low"]

class Overview(BaseModel):
    endpoints: int
    healthy: int
    warning: int
    critical: int
    active_incidents: int
    network_alerts: int
    honeypot_attacks: int
    hardware_warnings: int

class Incident(BaseModel):
    id: str
    title: str
    severity: Severity
    asset: str
    source: str
    status: str
    created_at: str

class Endpoint(BaseModel):
    hostname: str
    status: str
    security_risk: int
    hardware_risk: int
    cpu: int
    gpu: int
