from sqlalchemy import func, select

from app.db.models import Event, IncidentEvent, Notification
from app.ingest import ingest_normalized
from app.notifications.service import enqueue_for_incident
from tests.conftest import mk_event


def test_same_event_twice_one_row(session, settings):
    ev = mk_event("dup1")
    ingest_normalized(session, [ev, ev], settings)
    ingest_normalized(session, [ev], settings)
    session.commit()
    assert session.scalar(select(func.count()).select_from(Event)) == 1
    assert session.scalar(select(func.count()).select_from(IncidentEvent)) == 1


def test_reingest_fixtures_changes_nothing(loaded, session, settings):
    import asyncio
    from app.connectors.cryptoguard import build_connectors
    from app.ingest import run_ingest

    before = session.scalar(select(func.count()).select_from(Event))
    res = asyncio.run(run_ingest(session, settings, build_connectors(settings)))
    session.commit()
    # Explicit fixture ingest is TEST; REAL and TEST copies intentionally coexist.
    assert res["new"] == before
    again = asyncio.run(run_ingest(session, settings, build_connectors(settings)))
    assert again["new"] == 0 and session.scalar(select(func.count()).select_from(Event)) == before * 2


def test_notification_idempotency_key(loaded, session, settings):
    from app.db.models import Incident

    inc = session.scalars(select(Incident)).one()
    enqueue_for_incident(session, inc, settings)  # key = incident:version:channel
    n = session.scalar(select(func.count()).select_from(Notification))
    assert enqueue_for_incident(session, inc, settings) == 0  # same version again -> no duplicates
    assert session.scalar(select(func.count()).select_from(Notification)) == n
