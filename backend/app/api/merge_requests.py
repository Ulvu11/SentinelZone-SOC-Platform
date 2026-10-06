from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.auth.permissions import require
from app.db.models import MergeRequest
from app.db.session import get_db
from app.incidents import service
from app.incidents.models import Conflict, NotFound

router = APIRouter(prefix="/v1/merge-requests", tags=["merge-requests"])


def _out(m: MergeRequest) -> dict:
    return {"id": m.id, "source_id": f"SZ-{m.source_id:06d}", "target_id": f"SZ-{m.target_id:06d}", "status": m.status,
            "requested_by": m.requested_by, "decided_by": m.decided_by, "created_at": m.created_at, "decided_at": m.decided_at}


@router.get("")
def list_requests(status: str | None = None, limit: int = Query(50, ge=1, le=200), db=Depends(get_db), _=Depends(require("read"))):
    q = select(MergeRequest)
    if status:
        q = q.where(MergeRequest.status == status)
    return {"items": [_out(m) for m in db.scalars(q.order_by(MergeRequest.id.desc()).limit(limit))]}


def _decide(db, mid: int, approve: bool, actor: str):
    try:
        return _out(service.decide_merge(db, mid, approve, actor))
    except NotFound as e:
        raise HTTPException(404, f"not found: {e}")
    except Conflict as e:
        raise HTTPException(409, {"message": str(e)})
    except PermissionError as e:
        raise HTTPException(403, str(e))


@router.post("/{mid}/approve")
def approve(mid: int, db=Depends(get_db), p=Depends(require("merge"))):
    return _decide(db, mid, True, p.name)


@router.post("/{mid}/reject")
def reject(mid: int, db=Depends(get_db), p=Depends(require("merge"))):
    return _decide(db, mid, False, p.name)
