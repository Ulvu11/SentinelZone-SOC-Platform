"""Optional in-process scheduler (INGEST_INTERVAL_SECONDS / DISPATCH_INTERVAL_SECONDS, 0 = off).
Safe with several workers: ingest takes a PostgreSQL advisory lock, dispatch uses FOR UPDATE SKIP LOCKED."""
import asyncio
import logging
from contextlib import asynccontextmanager

from app.config import get_settings
from app.connectors.cryptoguard import build_connectors
from app.db.session import get_session_factory
from app.ingest import run_ingest, try_ingest_lock
from app.notifications.outbox import dispatch_due
from app.notifications.senders import build_senders

log = logging.getLogger("sentinelzone.scheduler")


async def ingest_once(settings=None, factory=None) -> dict | None:
    settings = settings or get_settings()
    db = (factory or get_session_factory(settings))(info={"tenant_id":settings.default_tenant_id})
    try:
        if not try_ingest_lock(db):
            return None
        res = await run_ingest(db, settings, build_connectors(settings))
        db.commit()
        return res
    except Exception:
        db.rollback()
        log.exception("scheduled ingest failed")
        return None
    finally:
        db.close()


def dispatch_once(settings=None, factory=None) -> dict | None:
    settings = settings or get_settings()
    db = (factory or get_session_factory(settings))(info={"tenant_id":settings.default_tenant_id})
    try:
        tg, sms = build_senders(settings)
        stats = dispatch_due(db, settings, tg, sms_sender=sms)
        db.commit()
        return stats
    except Exception:
        db.rollback()
        log.exception("scheduled dispatch failed")
        return None
    finally:
        db.close()


async def _loop(interval: int, fn):
    while True:
        try:
            await fn()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("scheduler loop error")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app):
    s = app.state.settings.validate_runtime()
    tasks = []
    if s.ingest_interval_seconds > 0:
        tasks.append(asyncio.create_task(_loop(s.ingest_interval_seconds, ingest_once)))
    if s.dispatch_interval_seconds > 0:
        tasks.append(asyncio.create_task(_loop(s.dispatch_interval_seconds, lambda: asyncio.to_thread(dispatch_once))))
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
