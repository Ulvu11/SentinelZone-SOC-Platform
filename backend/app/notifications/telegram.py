from dataclasses import dataclass

import httpx


@dataclass
class SendResult:
    kind: str  # success | retry | failed
    http_status: int | None = None
    retry_after: int | None = None
    error: str | None = None


class TelegramSender:
    def __init__(self, token: str, chat_id: str, client: httpx.Client | None = None, timeout: float = 10.0):
        self.token, self.chat_id, self.timeout = token, chat_id, timeout
        self._client = client

    def send(self, text: str) -> SendResult:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            c = self._client or httpx.Client(timeout=self.timeout)
            r = c.post(url, json={"chat_id": self.chat_id, "text": text})
        except httpx.HTTPError:  # DNS outage, timeout, connection reset ... (error text may contain the token URL, so we drop it)
            return SendResult("retry", error="network_error")
        if r.status_code == 200:
            try:
                ok = r.json().get("ok") is True
            except ValueError:
                ok = False
            return SendResult("success", 200) if ok else SendResult("failed", 200, error="ok_false")
        if r.status_code == 429:
            try:
                ra = int(r.json().get("parameters", {}).get("retry_after", 30))
            except (ValueError, AttributeError):
                ra = 30
            return SendResult("retry", 429, retry_after=ra, error="rate_limited")
        if r.status_code >= 500:
            return SendResult("retry", r.status_code, error=f"server_error_{r.status_code}")
        return SendResult("failed", r.status_code, error=f"client_error_{r.status_code}")  # invalid token / chat -> no retry
