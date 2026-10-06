from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.db.models import ConnectorState

SOURCES = ("splunk", "wazuh", "cryptoguard")


def connector_states(session, settings=None) -> dict[str, dict]:
    """Per-source health. A source that answered OK long ago is reported 'degraded' (stale), never silently 'healthy'."""
    settings = settings or get_settings()
    stale_after = settings.stale_after_minutes * 60
    now = datetime.now(timezone.utc)
    rows = {r.source: r for r in session.scalars(select(ConnectorState))}
    out = {}
    for s in SOURCES:
        if s == 'cryptoguard' and not settings.cryptoguard_url:
            from app.cryptoguard.models import CryptoGuardAgent
            agents = list(session.scalars(select(CryptoGuardAgent).where(CryptoGuardAgent.enabled.is_(True))))
            if agents:
                latest = max((a.last_received_at for a in agents if a.last_received_at), default=None)
                observed = max((a.last_observed_at for a in agents if a.last_observed_at), default=None)
                healthy = all(a.last_received_at and a.last_observed_at and (now-a.last_received_at).total_seconds()<180 and (now-a.last_observed_at).total_seconds()<180 for a in agents)
                out[s] = {'source':s,'status':'healthy' if healthy else 'degraded','mode':'live',
                    'transport':'agent_push','last_success_at':latest,'last_event_at':observed,
                    'error':None if healthy else 'one_or_more_agents_stale',
                    'cache_age_seconds':int((now-latest).total_seconds()) if latest else None}
                continue
        r = rows.get(s)
        status = r.status if r else ("not_configured" if not getattr(settings, s + "_url") and not settings.allow_fixtures else "unknown")
        age = int((now - r.last_success_at).total_seconds()) if r and r.last_success_at else None
        error = r.error if r else None
        mode = r.mode if r else None
        if settings.app_env == "production" and not getattr(settings, s + "_url"):
            status, mode, error = "not_configured", "not_configured", "connector URL not configured"
        elif mode == "fixture":
            status = "degraded"

        if status == "healthy" and age is not None and age > stale_after:
            status, error = "degraded", f"stale: no successful poll for {age}s"
        out[s] = {
            "source": s, "status": status, "mode": mode,
            "last_success_at": r.last_success_at if r else None, "last_event_at": r.last_event_at if r else None,
            "error": error, "cache_age_seconds": age,
        }
    return out


def data_complete(states: dict[str, dict]) -> bool:
    """False if any source is not healthy -> '0 alerts' must NOT be read as 'all clear'."""
    return bool(states) and all(s["status"] == "healthy" and s.get("mode") == "live" for s in states.values())
