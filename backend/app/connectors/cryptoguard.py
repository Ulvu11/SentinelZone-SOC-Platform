from app.connectors.base import Connector, ConnectorError, ConnectorHealth, RawEvent


class CryptoGuardConnector(Connector):
    """If the CryptoGuard API contract changes, ONLY this file (and its normalizer) changes."""

    name = "cryptoguard"
    fixture_subdir = "cryptoguard"

    @property
    def base_url(self) -> str:
        return self.settings.cryptoguard_url

    @property
    def ca_file(self) -> str:
        return self.settings.cryptoguard_ca_file

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.settings.cryptoguard_read_key}"}

    async def health(self) -> ConnectorHealth:
        if self.mode == "not_configured":
            return ConnectorHealth(source=self.name, status="not_configured", mode="not_configured")
        if self.mode == "fixture":
            return ConnectorHealth(source=self.name, status="degraded", mode="fixture")
        try:
            await self._request("GET", "/health")
            return ConnectorHealth(source=self.name, status="healthy", mode="live")
        except ConnectorError as e:
            return ConnectorHealth(source=self.name, status="unavailable", mode="live", error=str(e))

    async def fetch_events(self, since, until) -> list[RawEvent]:
        self.require_configured()
        path = ["cryptoguard-backend"]
        if self.mode == "fixture":
            return [RawEvent("cryptoguard", p, path) for p in self.load_fixture_files()]
        params = {"since": since.isoformat()} if since else {}
        if until:
            params["until"] = until.isoformat()
        rows, seen = [], set()
        while True:
            data = (await self._request("GET", self.settings.cryptoguard_events_path, params=params)).json()
            if isinstance(data, list):
                items, cursor = data, None
            elif isinstance(data, dict) and isinstance(data.get("items"), list):
                items, cursor = data["items"], data.get("next_cursor")
            else:
                raise ConnectorError("unsupported_cryptoguard_contract")
            rows.extend(items)
            if len(rows) > self.settings.max_ingest_events:
                raise ConnectorError("cryptoguard_batch_limit_exceeded")
            if not cursor:
                break
            if not isinstance(cursor, str) or cursor in seen:
                raise ConnectorError("invalid_cryptoguard_cursor")
            seen.add(cursor)
            params["cursor"] = cursor
        return [RawEvent("cryptoguard", p, path) for p in rows]


def build_connectors(settings):
    from app.connectors.splunk import SplunkConnector
    from app.connectors.wazuh import WazuhConnector

    return [SplunkConnector(settings), WazuhConnector(settings), CryptoGuardConnector(settings)]
