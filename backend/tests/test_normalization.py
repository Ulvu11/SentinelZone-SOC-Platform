import json
from datetime import datetime, timezone
from pathlib import Path

from app.normalization.normalizer import normalize

FX = Path(__file__).resolve().parent.parent / "fixtures"
NOW = datetime(2026, 10, 4, 12, 30, 3, tzinfo=timezone.utc)


def load(p):
    return json.loads((FX / p).read_text())


def test_wazuh_via_splunk_is_one_sensor_two_collectors():
    ev = normalize("wazuh", load("wazuh/high.json"), ["wazuh-manager", "splunk"], NOW)
    assert ev.source == ev.original_sensor == "wazuh"
    assert ev.collector_path == ["wazuh-manager", "splunk"]
    assert ev.evidence_ref.startswith("splunk:")
    assert (ev.original_severity, ev.severity_system, ev.normalized_priority) == ("10", "wazuh", "high")
    assert ev.host_id == "WEB01" and ev.agent_ip == "10.10.20.10" and ev.src_ip is None


def test_event_time_and_received_at_are_separate():
    ev = normalize("wazuh", load("wazuh/high.json"), ["wazuh-manager"], NOW)
    assert ev.event_time.isoformat().startswith("2026-10-04T12:29:00")
    assert ev.received_at == NOW


def test_same_event_different_collector_same_uid():
    a = normalize("wazuh", load("wazuh/high.json"), ["wazuh-manager"], NOW)
    b = normalize("wazuh", load("wazuh/high.json"), ["wazuh-manager", "splunk"], NOW)
    assert a.event_uid == b.event_uid


def test_suricata_keeps_src_dst_and_no_agent_ip():
    ev = normalize("suricata", load("suricata/scan.json"), ["suricata"], NOW)
    assert ev.src_ip == "10.10.30.10" and ev.dst_ip == "10.10.20.10" and ev.agent_ip is None
    assert ev.normalized_priority == "high"


def test_cowrie_never_carries_password():
    ev = normalize("cowrie", load("cowrie/login.json"), ["cowrie"], NOW)
    assert "REDACTED" not in ev.model_dump_json() and "password" not in ev.model_dump_json().lower()


def test_cryptoguard_priority_mapping():
    hi = normalize("cryptoguard", load("cryptoguard/high-risk.json"), ["cryptoguard-backend"], NOW)
    lo = normalize("cryptoguard", load("cryptoguard/normal.json"), ["cryptoguard-backend"], NOW)
    assert hi.normalized_priority == "high" and lo.normalized_priority == "low"
    assert "unsigned_process" in hi.summary
