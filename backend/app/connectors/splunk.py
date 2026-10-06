import json
import re
from datetime import datetime, timezone, timedelta

from app.connectors.base import Connector, ConnectorHealth, ConnectorError, RawEvent

# Only allowlisted SPL is ever executed. No free-form SPL from clients.
INGEST_SPL = 'search ((index=wazuh source="/var/ossec/logs/alerts/alerts.json") OR (index=suricata sourcetype=suricata*) OR (index=cowrie sourcetype=cowrie*))'
APPROVED_HUNTS = {
    "cowrie-failed-logins": 'search index={index} sourcetype=cowrie* "cowrie.login.failed" | stats count by src_ip | head 100',
    "suricata-high-severity": 'search index={index} sourcetype=suricata* alert.severity=1 | stats count by src_ip, dest_ip | head 100',
}
_KIND = {"wazuh": "wazuh", "suricata": "suricata", "cowrie": "cowrie"}


class SplunkConnector(Connector):
    name = "splunk"
    fixture_subdir = "splunk"

    @property
    def base_url(self) -> str:
        return self.settings.splunk_url

    @property
    def ca_file(self) -> str:
        return self.settings.splunk_ca_file

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.settings.splunk_token}"}  # read-only token

    async def health(self) -> ConnectorHealth:
        if self.mode == "not_configured":
            return ConnectorHealth(source=self.name, status="not_configured", mode="not_configured")
        if self.mode == "fixture":
            return ConnectorHealth(source=self.name, status="degraded", mode="fixture")
        try:
            await self._request("GET", "/services/server/info", params={"output_mode": "json"})
            return ConnectorHealth(source=self.name, status="healthy", mode="live")
        except ConnectorError as e:
            return ConnectorHealth(source=self.name, status="unavailable", mode="live", error=str(e))

    @staticmethod
    def _to_raw(row: dict) -> RawEvent | None:
        st = str(row.get("sourcetype", "")).split(":")[0].lower()
        kind = _KIND.get(st)
        if row.get('index') == 'wazuh' and row.get('source') == '/var/ossec/logs/alerts/alerts.json':
            kind = 'wazuh'
        if not kind:
            return None
        raw = row.get("_raw")
        try:
            if isinstance(raw, str):
                # Real EVE UDP input is RFC3164 syslog followed by one JSON object.
                if kind == 'suricata' and not raw.lstrip().startswith('{'):
                    match = re.match(r'^.{0,512}?\bsuricata\[\d+\]:\s*(\{.*)$', raw, re.S)
                    raw = match.group(1) if match else raw
                payload = json.loads(raw)
            else:
                payload = raw
            if not isinstance(payload, dict): payload = {}
        except (ValueError, TypeError):
            # Count a rejected source record in normalization; one truncated UDP
            # message must not abort every healthy record in the search window.
            payload = {}
        return RawEvent(kind=kind, payload=payload, collector_path=_path(kind))

    async def fetch_events(self, since, until) -> list[RawEvent]:
        self.require_configured()
        if self.mode == "fixture":
            return [r for r in (self._to_raw(x) for x in self.load_fixture_files()) if r]
        spl = INGEST_SPL.format(index=self.settings.splunk_index)
        data = {"search": spl, "output_mode": "json", "exec_mode": "oneshot"}
        if since:
            data["earliest_time"] = since.astimezone(timezone.utc).isoformat()
        elif until:
            data["earliest_time"] = (until-timedelta(hours=self.settings.splunk_bootstrap_hours)).astimezone(timezone.utc).isoformat()
        if until:
            data["latest_time"] = until.astimezone(timezone.utc).isoformat()
        resp = await self._request("POST", "/services/search/jobs/export", data=data)
        out = []
        for line in resp.text.splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if any(str(m.get("type", "")).upper() in {"ERROR", "FATAL"} for m in entry.get("messages", [])):
                raise ConnectorError("splunk_search_failed")
            row = entry.get("result")
            if row and (r := self._to_raw(row)):
                out.append(r)
                if len(out) > self.settings.max_ingest_events:
                    raise ConnectorError("splunk_batch_limit_exceeded")
        return out

    async def run_hunt(self, query_id: str) -> dict:
        self.require_configured()
        if query_id not in APPROVED_HUNTS:
            raise KeyError(query_id)
        if self.mode == "fixture":
            counts: dict[str, int] = {}
            for r in await self.fetch_events(None, None):
                if r.kind == "cowrie" and r.payload.get("src_ip"):
                    counts[r.payload["src_ip"]] = counts.get(r.payload["src_ip"], 0) + 1
            return {"query_id": query_id, "mode": "fixture", "rows": [{"src_ip": k, "count": v} for k, v in counts.items()]}
        spl = APPROVED_HUNTS[query_id].format(index=self.settings.splunk_index)
        resp = await self._request("POST", "/services/search/jobs/export", data={"search": spl, "output_mode": "json", "exec_mode": "oneshot"})
        rows = [json.loads(l)["result"] for l in resp.text.splitlines() if l.strip() and "result" in json.loads(l)]
        return {"query_id": query_id, "mode": "live", "rows": rows}


def _path(kind: str) -> list[str]:
    return {"wazuh": ["wazuh-manager", "splunk"]}.get(kind, [kind, "splunk"])
