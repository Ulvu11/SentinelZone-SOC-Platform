from app.normalization.common import evidence_ref, make_uid, parse_ts, stable_hash
from app.normalization.models import NormalizedEvent

_PRIO = {"cowrie.login.success": "high", "cowrie.command.input": "high", "cowrie.login.failed": "medium"}


def normalize_cowrie(p: dict, collector_path, received_at) -> NormalizedEvent:
    eid = p["eventid"]
    native = f"{p.get('session', '')}:{eid}:{p.get('timestamp')}" if p.get("session") else stable_hash(p)
    # NOTE: captured passwords / commands are intentionally NOT copied (safe metadata only).
    return NormalizedEvent(
        event_uid=make_uid("cowrie", native),
        event_time=parse_ts(p["timestamp"]),
        received_at=received_at,
        source="cowrie",
        original_sensor="cowrie",
        collector_path=collector_path,
        event_type="honeypot_activity",
        host_id=p.get("sensor"),
        src_ip=p.get("src_ip"),
        dst_ip=p.get("dst_ip"),
        dst_port=p.get("dst_port"),
        original_severity=eid,
        severity_system="cowrie",
        normalized_priority=_PRIO.get(eid, "low"),
        is_test=bool(p.get("is_test")),
        evidence_ref=evidence_ref("cowrie", collector_path, native),
        summary=f"honeypot {eid}",
        session_id=p.get("session"),
    )
