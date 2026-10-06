from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import Settings
from app.db.models import Notification, NotificationAttempt, Incident
from app.notifications.telegram import SendResult
from app.notifications.policy import suppression_reason
from app.db.tenancy import tenant_id, scoped_get


def safe_text(p: dict) -> str:
    """Incident summary + safe metadata only. Never raw events, passwords, tokens."""
    return (f"[SentinelZone {p.get('execution_mode', 'REAL')}] {p['priority'].upper()} incident {p['incident_id']}\n"
            f"Asset: {p.get('host_id') or 'unknown'} | Status: {p['status']}\n"
            f"Why: {', '.join(p.get('reason_codes', [])) or 'n/a'} | Events: {p.get('event_count', 0)}")


def dispatch_due(session, settings: Settings, telegram_sender, now: datetime | None = None, sms_sender=None) -> dict:
    now = now or datetime.now(timezone.utc)
    stats = {"sent": 0, "retry": 0, "failed": 0, "suppressed": 0}
    q = select(Notification).where(Notification.status == "PENDING", Notification.channel != "dashboard").with_for_update(skip_locked=True)  # PostgreSQL: safe with several dispatchers
    for n in session.scalars(q):
        inc = scoped_get(session, Incident, n.incident_id)
        reason = suppression_reason(settings, inc, n.channel, tenant_id(session))
        if reason:
            n.status, n.suppression_reason, n.last_error = "SUPPRESSED", reason, reason
            stats["suppressed"] += 1
            continue
        if n.next_try_at and n.next_try_at > now:
            continue
        if n.channel == "telegram":
            if inc.execution_mode == "TEST":
                from app.notifications.telegram import TelegramSender
                test_sender = TelegramSender(settings.telegram_bot_token, settings.test_telegram_chat_id)
                res = test_sender.send(safe_text(n.payload))
            else:
                res = telegram_sender.send(safe_text(n.payload))
        elif sms_sender is not None:
            res = sms_sender.send(safe_text(n.payload))
        else:
            res = SendResult("failed", error="no_provider_configured")
        n.attempts += 1
        session.add(NotificationAttempt(notification_id=n.id, outcome=res.kind, http_status=res.http_status, error=res.error))
        if res.kind == "success":
            n.status, n.sent_at, n.last_error = "SENT", now, None
            stats["sent"] += 1
        elif res.kind == "retry" and n.attempts < settings.notify_max_attempts:  # bounded: never infinite
            delay = res.retry_after if res.retry_after else min(30 * 2 ** n.attempts, 3600)
            n.next_try_at, n.last_error = now + timedelta(seconds=delay), res.error
            stats["retry"] += 1
        else:
            n.status, n.last_error = "FAILED", res.error or "max_attempts_reached"
            stats["failed"] += 1
    return stats
