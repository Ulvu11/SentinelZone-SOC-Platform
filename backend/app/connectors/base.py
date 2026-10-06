import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

from app.config import Settings
from app.normalization.normalizer import normalize


@dataclass
class RawEvent:
    kind: str  # wazuh | suricata | cowrie | cryptoguard
    payload: dict
    collector_path: list[str] = field(default_factory=list)


class ConnectorHealth(BaseModel):
    source: str
    status: str  # healthy | degraded | unavailable | not_configured | unknown
    mode: str | None = None  # live | fixture | not_configured
    last_success_at: datetime | None = None
    last_event_at: datetime | None = None
    error: str | None = None
    cache_age_seconds: int | None = None  # now - last_success_at; large => data is stale


class ConnectorError(Exception):
    """Sanitized connector failure (never includes credentials)."""


class Connector(ABC):
    name: str = "base"
    fixture_subdir: str = ""

    def __init__(self, settings: Settings):
        self.settings = settings

    # ----- config hooks -----
    @property
    @abstractmethod
    def base_url(self) -> str: ...

    @property
    def ca_file(self) -> str:
        return ""

    @property
    def mode(self) -> str:
        if self.base_url:
            return "live"
        if self.settings.app_env in ("development", "test") and self.settings.allow_fixtures:
            return "fixture"
        return "not_configured"

    def require_configured(self):
        if self.mode == "not_configured":
            raise ConnectorError(f"{self.name}: not_configured")

    def _auth_headers(self) -> dict:
        return {}

    # ----- interface -----
    @abstractmethod
    async def health(self) -> ConnectorHealth: ...

    @abstractmethod
    async def fetch_events(self, since: datetime | None, until: datetime | None) -> list[RawEvent]: ...

    async def get_last_seen(self) -> datetime | None:
        times = []
        for raw in await self.fetch_events(None, None):
            try:
                times.append(normalize(raw.kind, raw.payload, raw.collector_path).event_time)
            except (KeyError, ValueError, TypeError):
                continue
        return max(times) if times else None

    # ----- helpers -----
    def load_fixture_files(self) -> list[dict]:
        if self.mode != "fixture":
            raise ConnectorError("fixture access forbidden")
        out: list[dict] = []
        for f in sorted(Path(self.settings.fixtures_dir, self.fixture_subdir).glob("*.json")):
            data = json.loads(f.read_text())
            out.extend(data if isinstance(data, list) else [data])
        return out

    async def _request(self, method: str, path: str, **kw) -> httpx.Response:
        verify = self.ca_file or True
        last: Exception | None = None
        for attempt in range(max(1, self.settings.connector_retries)):
            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url, timeout=self.settings.connector_timeout_seconds, verify=verify
                ) as c:
                    resp = await c.request(method, path, headers=self._auth_headers(), **kw)
                if resp.status_code >= 500:
                    raise ConnectorError(f"upstream_http_{resp.status_code}")
                if resp.status_code in (401, 403):
                    raise ConnectorError(f"upstream_auth_{resp.status_code}")
                resp.raise_for_status()
                return resp
            except ConnectorError as e:
                last = e
                if "auth" in str(e):
                    break  # retrying bad credentials is pointless
            except httpx.TimeoutException:
                last = ConnectorError("dependency timeout")
            except httpx.HTTPError as e:
                last = ConnectorError(f"upstream_error_{type(e).__name__}")
            await asyncio.sleep(0.5 * (attempt + 1))
        raise last or ConnectorError("unknown_error")
