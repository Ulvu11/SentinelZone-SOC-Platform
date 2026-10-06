import httpx
import secrets
from sqlalchemy import select

from app.config import Settings
from app.db.models import Incident, Notification, NotificationAttempt
from app.ingest import ingest_normalized
from app.notifications.outbox import dispatch_due, safe_text
from app.notifications.routing import channels_for
from app.notifications.telegram import TelegramSender
from tests.conftest import mk_event

MOCK_TOKEN = secrets.token_urlsafe(32)


def sender(handler):
    return TelegramSender(MOCK_TOKEN, "42", client=httpx.Client(transport=httpx.MockTransport(handler)))


def tg_settings(**kw):
    return Settings(telegram_enabled=True, sms_enabled=True, _env_file=None, **kw)


def pending(session):
    return session.scalars(select(Notification).where(Notification.channel == "telegram")).one()


def test_routing_table():
    assert channels_for("low") == ["dashboard"] and channels_for("medium") == ["dashboard"]
    assert channels_for("high") == ["dashboard", "telegram"]
    assert channels_for("critical") == ["dashboard", "telegram", "sms"]


def test_outbox_pipeline_and_channel_disabled(loaded, session):
    notes = {n.channel: n for n in session.scalars(select(Notification))}
    assert notes["dashboard"].status == "SENT"
    assert notes["telegram"].status == "SKIPPED" and notes["telegram"].last_error == "channel_disabled"


def test_legacy_notifier_blocks_dual_send(session):
    s = tg_settings(legacy_telegram_active=True)
    ingest_normalized(session, [mk_event("n1")], s)
    assert pending(session).status == "SKIPPED" and pending(session).last_error == "legacy_notifier_active"


def test_telegram_success(session):
    s = tg_settings()
    ingest_normalized(session, [mk_event("n2")], s)
    stats = dispatch_due(session, s, sender(lambda r: httpx.Response(200, json={"ok": True})))
    assert stats["sent"] == 1 and pending(session).status == "SENT"


def test_429_uses_retry_after_and_5xx_is_bounded(session):
    s = tg_settings(notify_max_attempts=2)
    ingest_normalized(session, [mk_event("n3")], s)
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    dispatch_due(session, s, sender(lambda r: httpx.Response(429, json={"parameters": {"retry_after": 77}})), now=now)
    n = pending(session)
    assert n.status == "PENDING" and int((n.next_try_at - now).total_seconds()) == 77
    dispatch_due(session, s, sender(lambda r: httpx.Response(502)), now=now + timedelta(seconds=100))
    assert pending(session).status == "FAILED"  # attempts exhausted -> no infinite retry


def test_invalid_token_fails_immediately_and_dns_outage_retries(session):
    s = tg_settings()
    ingest_normalized(session, [mk_event("n4")], s)
    dispatch_due(session, s, sender(lambda r: httpx.Response(401, json={"ok": False})))
    assert pending(session).status == "FAILED"

    ingest_normalized(session, [mk_event("n5", host="H9")], s)

    def dns(_):
        raise httpx.ConnectError(f"dns failure for bot {MOCK_TOKEN}")

    tg = session.scalars(select(Notification).where(Notification.channel == "telegram", Notification.status == "PENDING")).one()
    dispatch_due(session, s, sender(dns))
    assert tg.status == "PENDING" and tg.attempts == 1 and MOCK_TOKEN not in (tg.last_error or "")


def test_payload_has_no_secrets_or_raw_events(loaded, session):
    n = session.scalars(select(Notification).where(Notification.channel == "telegram")).one()
    text = safe_text(n.payload)
    for banned in ("password", "REDACTED", "token", "raw"):
        assert banned not in text.lower()
    assert "SZ-000001" in text and "Why:" in text
