import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

_NS = uuid.UUID("5b1f2c0e-6a54-4d3e-9a11-53e717e1a000")


def parse_ts(value) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    s = str(value).strip().replace("Z", "+00:00")
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)
    dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def stable_hash(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:32]


def make_uid(sensor: str, native_id: str) -> str:
    """Stable UUID: the same sensor event arriving via different collectors dedups to one row."""
    return str(uuid.uuid5(_NS, f"{sensor}:{native_id}"))


def evidence_ref(sensor: str, collector_path: list[str], native_id: str) -> str:
    via = collector_path[-1] if collector_path else sensor
    return f"{via}:{native_id}"
