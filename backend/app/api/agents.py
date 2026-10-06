from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.assets import _page
from app.auth.permissions import require
from app.db.models import Asset
from app.db.session import get_db

router = APIRouter(prefix="/v1", tags=["agents"])


@router.get("/agents")
def agents(limit: int = Query(100, ge=1, le=500), cursor: str | None = None, db=Depends(get_db), _=Depends(require("read"))):
    """Hosts that have a sensor agent (agent_id known)."""
    return _page(db, select(Asset).where(Asset.agent_id.is_not(None)), limit, cursor)
