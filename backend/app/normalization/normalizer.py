from datetime import datetime, timezone

from app.normalization.cowrie import normalize_cowrie
from app.normalization.cryptoguard import normalize_cryptoguard
from app.normalization.models import NormalizedEvent
from app.normalization.suricata import normalize_suricata
from app.normalization.wazuh import normalize_wazuh

NORMALIZERS = {
    "wazuh": normalize_wazuh,
    "suricata": normalize_suricata,
    "cowrie": normalize_cowrie,
    "cryptoguard": normalize_cryptoguard,
}


def normalize(kind: str, payload: dict, collector_path: list[str], received_at: datetime | None = None) -> NormalizedEvent:
    if kind not in NORMALIZERS:
        raise ValueError(f"unknown event kind: {kind}")
    return NORMALIZERS[kind](payload, list(collector_path), received_at or datetime.now(timezone.utc))
