import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock
import httpx
import pytest
from app.config import Settings
from app.connectors.wazuh import WazuhConnector
from app.connectors.cryptoguard import CryptoGuardConnector
from app.connectors.splunk import SplunkConnector
from app.connectors.base import ConnectorError
from app.main import create_app
from tests.conftest import T0


def test_wazuh_verified_offset_contract_and_upper_bound():
    c=WazuhConnector(Settings(wazuh_url="https://example.invalid",_env_file=None))
    c._authed=AsyncMock(side_effect=[httpx.Response(200,json={"data":{"affected_items":[{"id":"1"}],"total_affected_items":2}}),
                                     httpx.Response(200,json={"data":{"affected_items":[{"id":"2"}],"total_affected_items":2}})])
    assert len(asyncio.run(c.fetch_events(T0,T0)))==2
    assert c._authed.call_count==2
    assert c._authed.call_args.kwargs["params"]["until"]==T0.isoformat()


def test_wazuh_unknown_payload_fails_closed():
    c=WazuhConnector(Settings(wazuh_url="https://example.invalid",_env_file=None))
    c._authed=AsyncMock(return_value=httpx.Response(200,json={"unexpected":[]}))
    with pytest.raises(ConnectorError,match="contract"):asyncio.run(c.fetch_events(None,None))


def test_cryptoguard_cursor_contract():
    c=CryptoGuardConnector(Settings(cryptoguard_url="https://example.invalid",_env_file=None))
    c._request=AsyncMock(side_effect=[httpx.Response(200,json={"items":[{"event_id":"a"}],"next_cursor":"next"}),
                                     httpx.Response(200,json={"items":[{"event_id":"b"}]})])
    assert len(asyncio.run(c.fetch_events(T0,T0)))==2
    assert c._request.call_args.kwargs["params"]["cursor"]=="next"


def test_cryptoguard_repeated_cursor_fails_closed():
    c=CryptoGuardConnector(Settings(cryptoguard_url="https://example.invalid",_env_file=None))
    c._request=AsyncMock(return_value=httpx.Response(200,json={"items":[],"next_cursor":"same"}))
    with pytest.raises(ConnectorError,match="cursor"):asyncio.run(c.fetch_events(None,None))


def test_splunk_search_error_is_not_empty_success():
    c=SplunkConnector(Settings(splunk_url="https://example.invalid",_env_file=None))
    c._request=AsyncMock(return_value=httpx.Response(200,text=json.dumps({"messages":[{"type":"ERROR","text":"sensitive detail"}]})))
    with pytest.raises(ConnectorError,match="splunk_search_failed"):asyncio.run(c.fetch_events(None,None))


def test_runtime_openapi_matches_exported_contract():
    root=Path(__file__).resolve().parents[1]
    app=create_app(Settings(_env_file=None))
    saved=json.loads((root/"docs/openapi.json").read_text())
    assert app.openapi()==saved
    assert not any(path.startswith("/api/") for path in saved["paths"])
    for path in ("/v1/alerts","/v1/overview","/v1/metrics"):
        params={p["name"] for p in saved["paths"][path]["get"]["parameters"]}
        assert {"from","to"}<=params
    assert "agent_id" in {p["name"] for p in saved["paths"]["/v1/metrics"]["get"]["parameters"]}
