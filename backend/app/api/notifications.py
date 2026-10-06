from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.auth.permissions import require
from app.config import Settings, get_settings
from app.db.models import Notification
from app.db.session import get_db
from app.notifications.outbox import dispatch_due
from app.notifications.senders import build_senders

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


@router.get("")
def list_notifications(limit: int = Query(100, ge=1, le=500), cursor: int | None = None, status: str | None = None,
                       db=Depends(get_db), _=Depends(require("read"))):
    q = select(Notification)
    if status:
        q = q.where(Notification.status == status)
    if cursor:
        q = q.where(Notification.id < cursor)
    rows = list(db.scalars(q.order_by(Notification.id.desc()).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit]
    items = [{"id": n.id, "incident_id": f"SZ-{n.incident_id:06d}", "incident_version": n.incident_version, "channel": n.channel,
              "tenant_id":n.tenant_id, "template_version":n.template_version, "suppression_reason":n.suppression_reason, "status": n.status, "attempts": n.attempts, "next_try_at": n.next_try_at, "last_error": n.last_error,
              "created_at": n.created_at, "sent_at": n.sent_at} for n in rows]
    return {"items": items, "next_cursor": rows[-1].id if more and rows else None}


@router.post("/dispatch")
def dispatch(db=Depends(get_db), _=Depends(require("admin")), settings: Settings = Depends(get_settings)):
    tg, sms = build_senders(settings)
    stats = dispatch_due(db, settings, tg, sms_sender=sms)
    db.commit()
    return stats
