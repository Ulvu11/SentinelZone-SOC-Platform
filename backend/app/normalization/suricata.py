from app.normalization.common import evidence_ref, make_uid, parse_ts, stable_hash
from app.normalization.models import NormalizedEvent

_PRIO = {1: "high", 2: "medium", 3: "low"}


def normalize_suricata(p: dict, collector_path, received_at) -> NormalizedEvent:
    alert = p.get("alert") or {}
    sev = int(alert.get("severity", 3))
    # EVE flow_id identifies a flow, not a unique alert. Canonical occurrence identity
    # excludes forwarding/indexing metadata and normalizes equivalent timezone formats.
    identity = {
        "sensor": p.get("sensor_id") or p.get("sensor_name") or "suricata",
        "timestamp": parse_ts(p["timestamp"]).isoformat(timespec="microseconds"),
        "flow_id": str(p.get("flow_id", "")),
        "signature_id": str(alert.get("signature_id", "")),
        "gid": str(alert.get("gid", "")), "rev": str(alert.get("rev", "")),
        "src_ip": p.get("src_ip"), "src_port": p.get("src_port"),
        "dest_ip": p.get("dest_ip"), "dest_port": p.get("dest_port"),
        "proto": p.get("proto"), "event_type": p.get("event_type", "alert"),
        "tx_id": p.get("tx_id"), "pcap_cnt": p.get("pcap_cnt"),
    }
    native = stable_hash(identity)
    return NormalizedEvent(
        event_uid=make_uid("suricata", native),
        event_time=parse_ts(p["timestamp"]),
        received_at=received_at,
        source="suricata",
        original_sensor="suricata",
        collector_path=collector_path,
        event_type="network_alert" if alert else "telemetry",
        host_id=None,  # resolved from dst_ip -> asset during ingest
        src_ip=p.get("src_ip"),
        dst_ip=p.get("dest_ip"),
        dst_port=p.get("dest_port"),
        original_severity=str(sev),
        severity_system="suricata",
        normalized_priority=_PRIO.get(sev, "low") if alert else "low",
        is_test=bool(p.get("is_test")),
        evidence_ref=evidence_ref("suricata", collector_path, native),
        summary=alert.get("signature"),
        session_id=str(p["flow_id"]) if p.get("flow_id") else None,
    )
