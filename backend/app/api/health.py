from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import __version__
from app.api.common import connector_states
from app.db.session import get_db
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db=Depends(get_db), settings=Depends(get_settings)):
    now = datetime.now(timezone.utc).isoformat()
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "down", "database": "unavailable", "connectors": {}, "version": __version__, "time": now})
    states = connector_states(db,settings)
    conns = {k: v["status"] for k, v in states.items()}
    overall = "ok" if all(v == "healthy" for v in conns.values()) else "degraded"
    return {"status": overall, "database": "healthy", "connectors": conns, "version": __version__, "time": now}
