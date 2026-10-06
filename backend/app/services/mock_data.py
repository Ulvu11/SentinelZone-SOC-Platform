from app.schemas.models import Endpoint, Incident, Overview

OVERVIEW = Overview(
    endpoints=12,
    healthy=8,
    warning=2,
    critical=2,
    active_incidents=4,
    network_alerts=17,
    honeypot_attacks=43,
    hardware_warnings=3,
)

INCIDENTS = [
    Incident(id="INC-0148", title="Possible Resource Hijacking", severity="critical", asset="FINANCE-PC-02", source="CryptoGuard + Wazuh", status="Investigating", created_at="2026-09-15T18:21:00+04:00"),
    Incident(id="INC-0147", title="SSH Brute Force Against Honeypot", severity="high", asset="HP-COWRIE01", source="Cowrie", status="Open", created_at="2026-09-15T17:54:00+04:00"),
    Incident(id="INC-0146", title="Possible SQL Injection", severity="high", asset="WEB01", source="Splunk", status="Open", created_at="2026-09-15T17:10:00+04:00"),
    Incident(id="INC-0145", title="Port Scan Detected", severity="medium", asset="DMZ", source="Suricata", status="Acknowledged", created_at="2026-09-15T16:43:00+04:00"),
]

ENDPOINTS = [
    Endpoint(hostname="FINANCE-PC-02", status="Critical", security_risk=94, hardware_risk=71, cpu=91, gpu=94),
    Endpoint(hostname="WEB01", status="Warning", security_risk=78, hardware_risk=22, cpu=58, gpu=2),
    Endpoint(hostname="CLIENT01", status="Healthy", security_risk=18, hardware_risk=20, cpu=23, gpu=5),
    Endpoint(hostname="DC01", status="Healthy", security_risk=12, hardware_risk=16, cpu=31, gpu=0),
]
