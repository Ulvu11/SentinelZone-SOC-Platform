import httpx

from app.notifications.telegram import SendResult


class WebhookSmsProvider:
    """Provider-agnostic SMS: POSTs {"to","message"} to your SMS gateway (SMS_WEBHOOK_URL) with a bearer token.
    Swap this class (same .send(text) -> SendResult contract) to integrate a specific vendor."""

    def __init__(self, url: str, token: str, to: str, client: httpx.Client | None = None, timeout: float = 10.0):
        self.url, self.token, self.to, self.timeout, self._client = url, token, to, timeout, client

    def send(self, text: str) -> SendResult:
        try:
            c = self._client or httpx.Client(timeout=self.timeout)
            r = c.post(self.url, json={"to": self.to, "message": text}, headers={"Authorization": f"Bearer {self.token}"})
        except httpx.HTTPError:
            return SendResult("retry", error="network_error")
        if 200 <= r.status_code < 300:
            return SendResult("success", r.status_code)
        if r.status_code == 429:
            try:
                ra = int(r.headers.get("Retry-After", 30))
            except ValueError:
                ra = 30
            return SendResult("retry", 429, retry_after=ra, error="rate_limited")
        if r.status_code >= 500:
            return SendResult("retry", r.status_code, error=f"server_error_{r.status_code}")
        return SendResult("failed", r.status_code, error=f"client_error_{r.status_code}")
