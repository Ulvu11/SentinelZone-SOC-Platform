from app.connectors.base import Connector, ConnectorError, ConnectorHealth, RawEvent


class WazuhConnector(Connector):
    """READ-ONLY Wazuh API user. Live alert path is configurable (WAZUH_ALERTS_PATH)."""

    name = "wazuh"
    fixture_subdir = "wazuh"

    @property
    def base_url(self) -> str:
        return self.settings.wazuh_url

    @property
    def ca_file(self) -> str:
        return self.settings.wazuh_ca_file

    async def _token(self) -> str:
        import httpx

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url, timeout=self.settings.connector_timeout_seconds, verify=self.ca_file or True
            ) as c:
                r = await c.post(
                    "/security/user/authenticate",
                    params={"raw": "true"},
                    auth=(self.settings.wazuh_username, self.settings.wazuh_password),
                )
            if r.status_code in (401, 403):
                raise ConnectorError("upstream_auth_failed")
            r.raise_for_status()
            return r.text.strip()
        except httpx.TimeoutException:
            raise ConnectorError("dependency timeout")
        except httpx.HTTPError as e:
            raise ConnectorError(f"upstream_error_{type(e).__name__}")

    async def _authed(self, path: str, **kw):
        token = await self._token()
        self._bearer = token
        return await self._request("GET", path, **kw)

    def _auth_headers(self) -> dict:
        t = getattr(self, "_bearer", None)
        return {"Authorization": f"Bearer {t}"} if t else {}

    async def health(self) -> ConnectorHealth:
        if self.mode == "not_configured":
            return ConnectorHealth(source=self.name, status="not_configured", mode="not_configured")
        if self.mode == "fixture":
            return ConnectorHealth(source=self.name, status="degraded", mode="fixture")
        try:
            await self._authed("/manager/status")
            return ConnectorHealth(source=self.name, status="healthy", mode="live")
        except ConnectorError as e:
            return ConnectorHealth(source=self.name, status="unavailable", mode="live", error=str(e))

    async def fetch_events(self, since, until) -> list[RawEvent]:
        self.require_configured()
        path = ["wazuh-manager"]
        if self.mode == "fixture":
            return [RawEvent("wazuh", p, path) for p in self.load_fixture_files()]
        params = {"limit": 500, "offset": 0}
        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()
        rows = []
        while True:
            data = (await self._authed(self.settings.wazuh_alerts_path, params=params)).json()
            if isinstance(data, list):
                items, total = data, None
            elif isinstance(data, dict):
                payload = data.get("data", data)
                items = payload.get("items", payload.get("affected_items"))
                total = payload.get("total_affected_items", payload.get("total"))
                if not isinstance(items, list):
                    raise ConnectorError("unsupported_wazuh_alerts_contract")
            else:
                raise ConnectorError("unsupported_wazuh_alerts_contract")
            rows.extend(items)
            if len(rows) > self.settings.max_ingest_events:
                raise ConnectorError("wazuh_batch_limit_exceeded")
            if total is not None:
                if not isinstance(total, int) or total < len(rows):
                    raise ConnectorError("invalid_wazuh_pagination")
                if len(rows) >= total:
                    break
                if not items:
                    raise ConnectorError("incomplete_wazuh_pagination")
            elif len(items) < params["limit"]:
                break
            else:
                raise ConnectorError("unverified_wazuh_pagination_contract")
            params["offset"] = len(rows)
        return [RawEvent("wazuh", p, path) for p in rows]
