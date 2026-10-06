import asyncio
import os
import secrets
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.connectors.cryptoguard import build_connectors
from app.db.models import Base
from app.db.session import get_db
from app.ingest import run_ingest
from app.connectors.base import Connector
from app.main import create_app
from app.normalization.models import NormalizedEvent

_TDB = os.environ.get("TEST_DATABASE_URL", "")
if _TDB and "test" not in (make_url(_TDB).database or "").lower():
    raise RuntimeError("TEST_DATABASE_URL must point to a throw-away database whose name contains 'test' (the suite DROPS all tables)")

ROLE_TOKENS = {role: secrets.token_urlsafe(32) for role in ("v", "a", "o", "ad")}
TOKENS = ";".join(f"{ROLE_TOKENS[short]}:{name}:{role}" for short, name, role in
                  (("v", "vic", "viewer"), ("a", "ann", "analyst"), ("o", "omar", "operator"), ("ad", "root", "admin")))
T0 = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def settings():
    return Settings(allow_fixtures=True, auth_tokens=TOKENS, _env_file=None)


@pytest.fixture
def engine():
    """SQLite in-memory by default; set TEST_DATABASE_URL to run the whole suite on PostgreSQL."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        e = create_engine(url, pool_pre_ping=True)
        Base.metadata.drop_all(e)
        Base.metadata.create_all(e)
        yield e
        e.dispose()
        return
    e = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    @event.listens_for(e, "connect")
    def enable_constraints(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(e)
    yield e


@pytest.fixture
def session(engine):
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    yield s
    s.close()


@pytest.fixture
def client(engine, settings):
    app = create_app()
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def _db():
        db = factory()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def auth(role: str) -> dict:
    return {"Authorization": f"Bearer {ROLE_TOKENS[role]}"}


@pytest.fixture
def loaded(session, settings):
    """Fixtures -> normalizer -> DB -> correlation -> incident -> notification outbox."""
    # Recorded payloads simulate live API responses in an isolated test DB.
    # The separate integration test exercises the actual explicit TEST fixture path.
    class RecordedLive:
        mode = "live"
        def __init__(self, connector): self.connector, self.name = connector, connector.name
        async def fetch_events(self, since, until):
            return await self.connector.fetch_events(since, until)
    result = asyncio.run(run_ingest(session, settings, [RecordedLive(c) for c in build_connectors(settings)]))
    session.commit()
    return result


def mk_event(uid, host="HOST1", sensor="wazuh", prio="high", minutes=0, **kw) -> NormalizedEvent:
    base = dict(
        event_uid=uid, event_time=T0 + timedelta(minutes=minutes), received_at=T0 + timedelta(minutes=minutes, seconds=3),
        source=sensor, original_sensor=sensor, collector_path=[sensor], event_type="test", host_id=host,
        agent_ip="10.0.0.1", severity_system=sensor, normalized_priority=prio, original_severity="8",
    )
    base.update(kw)
    return NormalizedEvent(**base)
