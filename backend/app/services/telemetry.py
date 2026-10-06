"""Sensor liveness is based on telemetry/heartbeats, never only on alert counts.
Without a declared heartbeat interval, absence of alerts is unknown, not offline.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.models import SensorState
from app.db.tenancy import scoped_get

KNOWN_SENSORS = ("wazuh", "cryptoguard", "suricata", "cowrie", "windows")


def record_telemetry(db, sensor, at, settings, host_id=None, is_alert=False):
    if at.tzinfo is None:
        raise ValueError("Telemetry timestamp requires timezone")
    now = datetime.now(timezone.utc)
    if at > now:
        # Future timestamps cannot indefinitely hold a source healthy.
        at = now
    state = scoped_get(db, SensorState, sensor)
    if state is None:
        state = SensorState(original_sensor=sensor, affected_assets=[])
        db.add(state)
    state.expected_interval = settings.sensor_intervals().get(sensor)
    state.last_telemetry_at = max([x for x in (state.last_telemetry_at, at) if x])
    if is_alert:
        state.last_event_at = max([x for x in (state.last_event_at, at) if x])
    if host_id:
        state.affected_assets = sorted(set(state.affected_assets or []) | {host_id})
    state.updated_at = now
    state.status = "healthy"
    db.flush()
    return state


def sensor_states(db, settings, now=None):
    now = now or datetime.now(timezone.utc)
    rows = {s.original_sensor: s for s in db.scalars(select(SensorState))}
    intervals = settings.sensor_intervals()
    out = {}
    for name in sorted(set(KNOWN_SENSORS) | set(rows) | set(intervals)):
        s = rows.get(name)
        interval = intervals.get(name)
        last = s.last_telemetry_at if s else None
        age = max(0, int((now-last).total_seconds())) if last else None
        if last is None:
            status = "unknown" if interval else "not_configured"
        elif interval is None:
            status = "unknown"  # telemetry observed; no liveness contract configured
        elif age > interval * settings.sensor_offline_multiplier:
            status = "offline"
        elif age > interval:
            status = "degraded"
        else:
            status = "healthy"
        out[name] = {"original_sensor":name, "last_event_at":s.last_event_at if s else None,
                     "last_telemetry_at":last, "expected_interval":interval, "status":status,
                     "affected_assets":s.affected_assets if s else [], "updated_at":s.updated_at if s else None,
                     "telemetry_age_seconds":age}
    return out
