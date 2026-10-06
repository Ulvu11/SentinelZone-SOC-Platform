"""Read-only SOC reports from tenant-scoped, persisted REAL observations."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from app.api.common import connector_states
from app.api.time_filters import time_range, within
from app.auth.permissions import require
from app.config import get_settings
from app.cryptoguard.models import CryptoGuardAgent, CryptoGuardEvent
from app.db.models import Event, Incident
from app.db.session import get_db
from app.db.tenancy import tenant_id

router = APIRouter(prefix="/v1/reports", tags=["reports"])
INCIDENT_LIMIT = 5000


def alert_row(row):
    return {"id": row.event_uid, "observed_at": row.event_time, "severity": row.normalized_priority,
            "source": row.original_sensor, "title": row.summary or row.event_type,
            "host": row.host_id, "source_ip": row.src_ip, "destination_ip": row.dst_ip}


def metric(value):
    return value.get("value") if isinstance(value, dict) and value.get("status") == "ok" else None


@router.get("/soc-summary")
def soc_summary(times=Depends(time_range), db=Depends(get_db), _=Depends(require("read")),
                settings=Depends(get_settings)):
    now = datetime.now(timezone.utc)
    end = times[1] or now
    start = times[0] or end - timedelta(hours=24)
    if start >= end or end - start > timedelta(days=31):
        raise HTTPException(422, "report range must be positive and no longer than 31 days")
    times = (start, end)
    # Telemetry is not an alert. Keep this definition aligned with the Alerts page.
    alert_filter = (Event.execution_mode == "REAL", Event.is_test.is_(False), Event.event_type != "telemetry")
    eq = within(select(Event).where(*alert_filter), Event.event_time, times)
    counts = db.execute(within(select(Event.normalized_priority, Event.original_sensor, func.count())
                               .where(*alert_filter), Event.event_time, times)
                        .group_by(Event.normalized_priority, Event.original_sensor)).all()
    by_severity, by_source = {}, {}
    for severity, source, count in counts:
        by_severity[severity] = by_severity.get(severity, 0) + count
        by_source[source] = by_source.get(source, 0) + count
    count = sum(by_severity.values())
    states = connector_states(db, settings)
    # An empty feed is not evidence that monitoring is configured or working.
    alerts_available = count > 0
    latest = list(db.scalars(eq.order_by(Event.event_time.desc(), Event.event_uid).limit(25)))
    priority = list(db.scalars(eq.where(Event.normalized_priority.in_(("critical", "high")))
                               .order_by(Event.event_time.desc(), Event.event_uid).limit(25)))
    iq = within(select(Incident).where(Incident.execution_mode == "REAL"), Incident.opened_at, times)
    statuses = dict(db.execute(within(select(Incident.status, func.count())
                                      .where(Incident.execution_mode == "REAL"), Incident.opened_at, times)
                               .group_by(Incident.status)).all())
    incident_count = sum(statuses.values())
    incidents_available = incident_count > 0 or alerts_available
    incidents = list(db.scalars(iq.order_by(Incident.opened_at.desc(), Incident.id.desc()).limit(INCIDENT_LIMIT)))
    identity_match = or_(*(func.lower(func.coalesce(Event.summary, "") + " " + Event.event_type).like("%" + word + "%")
                          for word in ("auth", "login", "logon")))
    identity_counts = dict(db.execute(within(select(Event.normalized_priority, func.count()).where(
        *alert_filter, Event.original_sensor == "wazuh", identity_match), Event.event_time, times)
        .group_by(Event.normalized_priority)).all())
    identity_total = sum(identity_counts.values())
    def source_summary(source):
        rows = dict(db.execute(within(select(Event.event_type, func.count()).where(
            Event.execution_mode == "REAL", Event.is_test.is_(False), Event.original_sensor == source),
            Event.event_time, times).group_by(Event.event_type)).all())
        return {"status": "available" if rows else "unavailable", "event_count": sum(rows.values()) if rows else None,
                "event_types": rows, "source": source}

    agents = list(db.scalars(select(CryptoGuardAgent).order_by(CryptoGuardAgent.agent_id).limit(501)))
    cg_rows = []
    for agent in agents[:500]:
        event = db.scalar(within(select(CryptoGuardEvent).where(CryptoGuardEvent.agent_id == agent.agent_id,
            CryptoGuardEvent.event_type.in_(("telemetry", "inventory", "risk"))), CryptoGuardEvent.observed_at, times)
            .order_by(CryptoGuardEvent.observed_at.desc(), CryptoGuardEvent.sequence.desc()).limit(1))
        if not event or not event.payload.get("snapshot"):
            continue
        snapshot = event.payload["snapshot"]
        host = snapshot["host"]
        risks = event.payload.get("risk", [])
        sensor_rows = snapshot.get("sensors", [])
        gpu = [metric(s.get("reading")) for s in sensor_rows if s.get("reading", {}).get("unit") == "percent"
               and (s.get("type") == "utilization" or "gpu" in s.get("device_id", "").lower())
               and metric(s.get("reading")) is not None]
        temp = [metric(s.get("reading")) for s in sensor_rows if s.get("type", "").lower() == "temperature"
                and s.get("reading", {}).get("unit") in ("celsius", "C", "°C") and metric(s.get("reading")) is not None]
        cg_rows.append({"agent_id": agent.agent_id, "hostname": host.get("hostname"), "platform": agent.platform,
            "observed_at": event.observed_at, "agent_version": event.payload.get("agent_version"),
            "cpu_percent": metric(host.get("cpu_percent")), "ram_percent": metric(host.get("memory_used_percent")),
            "gpu_percent": max(gpu, default=None), "temperature_c": max(temp, default=None),
            "security_risk": max((r["security_risk"] for r in risks), default=0),
            "resource_impact": max((r["resource_impact"] for r in risks if r.get("resource_impact") is not None), default=None),
            "assessment_source": "agent_heuristic"})
    return {
        "schema_version": "1.0", "title": "SOC Summary Report", "tenant": tenant_id(db), "generated_at": now,
        "time_range": {"from": start, "to": end, "boundary": "from inclusive, to exclusive"},
        "scope": "Persisted REAL data only. Alerts exclude telemetry. Incidents are selected by opened_at; status is current at generation.",
        "alerts": {"status": "available" if alerts_available else "unavailable", "count": count if alerts_available else None,
            "severity_distribution": by_severity, "source_distribution": by_source,
            "latest": [alert_row(row) for row in latest], "high_priority": [alert_row(row) for row in priority], "list_limit": 25},
        "incidents": {"status": "available" if incidents_available else "unavailable",
            "count": incident_count if incidents_available else None,
            "open_count": sum(n for status, n in statuses.items() if status not in ("RESOLVED", "CLOSED")) if incidents_available else None,
            "status_distribution": statuses, "items": [{"id": row.code, "title": row.title, "severity": row.priority,
                "status": row.status, "opened_at": row.opened_at, "host": row.host_id, "owner": row.owner} for row in incidents],
            "list_limit": INCIDENT_LIMIT, "list_truncated": incident_count > INCIDENT_LIMIT},
        "identity": {"status": "available" if identity_total else "unavailable", "event_count": identity_total or None,
            "severity_distribution": identity_counts,
            "method": "Wazuh event descriptions/types containing auth, login or logon; not a user inventory or a count of confirmed compromises."},
        "network": source_summary("suricata"), "honeypots": source_summary("cowrie"),
        "cryptoguard": {"status": "available" if cg_rows else "unavailable" if agents else "not_configured",
            "agents_with_telemetry": len(cg_rows) if cg_rows else None, "items": cg_rows, "list_truncated": len(agents) > 500,
            "scope": "Latest snapshot per agent within the selected range; security risk and resource impact are independent. Unavailable sensors remain null."},
        "connectors": {key: {"status": value["status"], "last_success_at": value.get("last_success_at"),
                             "last_event_at": value.get("last_event_at")} for key, value in states.items()},
        "data_complete": all(value["status"] == "healthy" for value in states.values()),
    }
