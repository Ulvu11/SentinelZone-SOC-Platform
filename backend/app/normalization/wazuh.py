from app.normalization.common import evidence_ref, make_uid, parse_ts, stable_hash
from app.normalization.models import NormalizedEvent


def _prio(level: int) -> str:
    return "critical" if level >= 12 else "high" if level >= 8 else "medium" if level >= 5 else "low"


def normalize_wazuh(p: dict, collector_path, received_at) -> NormalizedEvent:
    agent = p.get("agent") or {}
    rule = p["rule"]
    level = int(rule["level"])
    native = str(p.get("id") or stable_hash(p))
    return NormalizedEvent(
        event_uid=make_uid("wazuh", native),
        event_time=parse_ts(p["timestamp"]),
        received_at=received_at,
        source="wazuh",
        original_sensor="wazuh",
        collector_path=collector_path,
        event_type="endpoint_alert",
        host_id=agent.get("name"),
        agent_id=agent.get("id"),
        agent_ip=agent.get("ip"),
        src_ip=(p.get("data") or {}).get("srcip"),
        original_severity=str(level),
        severity_system="wazuh",
        normalized_priority=_prio(level),
        is_test=bool(p.get("is_test")),
        evidence_ref=evidence_ref("wazuh", collector_path, native),
        summary=rule.get("description"),
    )
