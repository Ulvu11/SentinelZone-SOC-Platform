from typing import Literal
from app.api.time_filters import time_range
from app.config import get_settings
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.common import connector_states, data_complete
from app.auth.permissions import require
from app.db.repositories.events import EventRepository, InvalidCursor
from app.db.session import get_db
from app.normalization.models import NormalizedEvent

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


@router.get("")
def list_alerts(
    limit: int = Query(100, ge=1, le=500), cursor: str | None = None, priority: str | None = None,
    source: str | None = None, host_id: str | None = None, include_test: bool = False,
    exclude_telemetry: bool = False,
    times=Depends(time_range), settings=Depends(get_settings), db=Depends(get_db), _=Depends(require("read")),
):
    try:
        rows, nxt = EventRepository(db).page(limit, cursor, priority, source, host_id, include_test, *times,
                                            exclude_telemetry=exclude_telemetry)
    except InvalidCursor:
        raise HTTPException(422, "invalid cursor")
    states = connector_states(db,settings)
    return {
        "items": [NormalizedEvent.model_validate(r) for r in rows],
        "next_cursor": nxt,
        "sources": {k: v["status"] for k, v in states.items()},
        "data_complete": data_complete(states),  # False => do not display "0 alerts" as healthy
    }


@router.get("/{event_uid}")
def get_alert(event_uid: str, execution_mode: Literal["REAL", "TEST"] = "REAL", db=Depends(get_db), _=Depends(require("read"))):
    repo = EventRepository(db)
    e = repo.get(event_uid, execution_mode)
    if e is None:
        raise HTTPException(404, "alert not found")
    return {**NormalizedEvent.model_validate(e).model_dump(), "external_refs": repo.refs(event_uid, execution_mode)}
