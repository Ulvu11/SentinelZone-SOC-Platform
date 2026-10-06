from datetime import datetime, timezone
from sqlalchemy import select,func
from app.db.models import Incident, IncidentEvent, Notification
from app.db.tenancy import tenant_id
from app.notifications.routing import channels_for
from app.notifications.policy import suppression_reason


def _payload(session, inc):
    count = session.scalar(select(func.count()).select_from(IncidentEvent).where(IncidentEvent.incident_id == inc.id))
    # Fixed allowlist. Raw evidence, event summaries, credentials and analyst notes never enter delivery payloads.
    return {"incident_id":inc.code, "priority":inc.priority, "status":inc.status, "host_id":inc.host_id,
            "reason_codes":list(inc.reason_codes or []), "event_count":count,
            "execution_mode":inc.execution_mode, "tenant_id":inc.tenant_id}


def enqueue_for_incident(session, inc: Incident, settings) -> int:
    if inc.execution_mode == "REPLAY":
        return 0
    if inc.tenant_id != tenant_id(session):
        raise ValueError("Cross-tenant notification denied")
    created, payload = 0, _payload(session, inc)
    for ch in channels_for(inc.priority):
        key = f"{inc.id}:{inc.version}:{ch}"
        if session.scalar(select(Notification.id).where(Notification.idempotency_key == key)):
            continue
        reason = suppression_reason(settings, inc, ch, tenant_id(session))
        status = "SKIPPED" if reason else ("SENT" if ch == "dashboard" else "PENDING")
        legacy_error = {"CHANNEL_DISABLED":"channel_disabled", "LEGACY_NOTIFIER_ACTIVE":"legacy_notifier_active", "POLICY_DENIED":"policy_denied"}.get(reason)
        if reason == "POLICY_DENIED" and settings.telegram_canary_enabled and inc.execution_mode == "REAL":
            legacy_error = "outside_canary"
        session.add(Notification(incident_id=inc.id, incident_version=inc.version, channel=ch,
            recipient_key="lab-test" if inc.execution_mode == "TEST" else "default", status=status,
            last_error=legacy_error, suppression_reason=reason, idempotency_key=key, payload=payload,
            template_version=settings.notification_template_version,
            sent_at=datetime.now(timezone.utc) if status == "SENT" else None))
        created += 1
    session.flush()
    return created
