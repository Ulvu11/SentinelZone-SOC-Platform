from app.normalization.common import evidence_ref, make_uid, parse_ts, stable_hash
from app.normalization.models import NormalizedEvent


def _prio(risk: int) -> str:
    return "critical" if risk >= 90 else "high" if risk >= 70 else "medium" if risk >= 40 else "low"


def normalize_cryptoguard(p: dict, collector_path, received_at) -> NormalizedEvent:
    risk = int(p["security_risk"])
    native = str(p.get("event_id") or stable_hash(p))
    reasons = ",".join(p.get("reasons") or [])
    return NormalizedEvent(
        event_uid=make_uid("cryptoguard", native),
        event_time=parse_ts(p["observed_at"]),
        received_at=received_at,
        source="cryptoguard",
        original_sensor="cryptoguard",
        collector_path=collector_path,
        event_type="behavioral_risk",
        host_id=p.get("hostname"),
        agent_id=p.get("agent_id"),
        agent_ip=p.get("ip"),
        original_severity=str(risk),
        severity_system="cryptoguard",
        normalized_priority=_prio(risk),
        is_test=bool(p.get("is_test")),
        evidence_ref=evidence_ref("cryptoguard", collector_path, native),
        summary=f"security_risk={risk} resource_impact={p.get('resource_impact')} reasons={reasons}",
    )
