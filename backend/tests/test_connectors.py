import asyncio
import secrets

import httpx
import pytest

from app.config import Settings
from app.connectors.base import ConnectorError
from app.connectors.cryptoguard import CryptoGuardConnector, build_connectors
from app.db.models import ConnectorState
from app.ingest import run_ingest


def test_fixture_mode_when_no_url(settings):
    for c in build_connectors(settings):
        assert c.mode == "fixture"
        assert asyncio.run(c.health()).status == "degraded"
        assert asyncio.run(c.get_last_seen()) is not None


def test_dead_source_does_not_crash_and_is_marked_unavailable(session):
    s = Settings(allow_fixtures=True, cryptoguard_url="http://127.0.0.1:9", connector_retries=1, connector_timeout_seconds=0.5, _env_file=None)
    res = asyncio.run(run_ingest(session, s, build_connectors(s)))
    session.commit()
    st = session.get(ConnectorState, ("lab", "cryptoguard"))
    assert st.status == "unavailable" and st.error
    assert session.get(ConnectorState, ("lab", "wazuh")).status == "degraded"  # partial response, others unaffected
    assert res["new"] > 0


def test_error_message_never_leaks_credentials():
    marker = secrets.token_urlsafe(32)
    s = Settings(allow_fixtures=True, cryptoguard_url="http://127.0.0.1:9", cryptoguard_read_key=marker, connector_retries=1, _env_file=None)
    h = asyncio.run(CryptoGuardConnector(s).health())
    assert h.status == "unavailable" and marker not in (h.error or "")
