from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response

from app.auth.permissions import get_principal, require
from app.auth.roles import Principal
from app.db.repositories.incidents import IncidentRepository
from app.db.session import get_db
from app.incidents import service
from app.incidents.models import Conflict, NotFound
from app.schemas import IncidentCreate, IncidentOut, IncidentPatch, MergeIn, NoteIn

router = APIRouter(prefix="/v1/incidents", tags=["incidents"])


def _call(fn, *a):
    try:
        return fn(*a)
    except NotFound as e:
        raise HTTPException(404, f"not found: {e}")
    except Conflict as e:
        detail = {"message": str(e)}
        if e.current_version is not None:
            detail["current_version"] = e.current_version
        raise HTTPException(409, detail)


@router.get("")
def list_incidents(limit: int = Query(50, ge=1, le=200), cursor: int | None = None, status: str | None = None,
                   priority: str | None = None, execution_mode: Literal["REAL", "TEST"] = "REAL", db=Depends(get_db), _=Depends(require("read"))):
    rows, nxt = IncidentRepository(db).page(limit, cursor, status, priority, execution_mode)
    return {"items": [service.to_out(db, i) for i in rows], "next_cursor": nxt}


@router.post("", status_code=201, response_model=IncidentOut)
def create_incident(body: IncidentCreate, db=Depends(get_db), p: Principal = Depends(require("investigate"))):
    return service.to_out(db, _call(service.create_manual, db, body, p.name))


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: str, response: Response, db=Depends(get_db), _=Depends(require("read"))):
    inc = _call(service.get_or_404, db, incident_id)
    response.headers["ETag"] = f'"{inc.version}"'
    return service.to_out(db, inc)


@router.get("/{incident_id}/timeline")
def get_timeline(incident_id: str, db=Depends(get_db), _=Depends(require("read"))):
    return {"items": _call(service.timeline, db, incident_id)}


@router.patch("/{incident_id}", response_model=IncidentOut)
def patch_incident(incident_id: str, body: IncidentPatch, if_match: str | None = Header(default=None, alias="If-Match"),
                   db=Depends(get_db), p: Principal = Depends(get_principal)):
    needed = "transition" if body.status else "investigate"
    if not p.can(needed):
        raise HTTPException(403, f"role '{p.role}' lacks permission '{needed}'")
    if if_match is None:
        raise HTTPException(428, "If-Match header (incident version) is required")
    try:
        expected = int(if_match.strip().strip('"'))
    except ValueError:
        raise HTTPException(422, "If-Match must be an integer version")
    inc = _call(service.update, db, incident_id, expected, body, p.name)
    return service.to_out(db, inc)


@router.post("/{incident_id}/notes", status_code=201)
def add_note(incident_id: str, body: NoteIn, db=Depends(get_db), p: Principal = Depends(require("investigate"))):
    n = _call(service.add_note, db, incident_id, body.body, p.name)
    return {"id": n.id, "actor": n.actor, "created_at": n.created_at, "body": n.body}


@router.post("/{incident_id}/merge")
def merge_incident(incident_id: str, body: MergeIn, response: Response, db=Depends(get_db), p: Principal = Depends(get_principal)):
    """Operator: merges now. Analyst: files a PENDING merge request that an operator must approve."""
    if p.can("merge"):
        return service.to_out(db, _call(service.merge, db, incident_id, body.target_id, p.name))
    if p.can("investigate"):
        mr = _call(service.request_merge, db, incident_id, body.target_id, p.name)
        response.status_code = 202
        return {"merge_request_id": mr.id, "status": mr.status, "note": "operator approval required"}
    raise HTTPException(403, f"role '{p.role}' lacks permission 'investigate'")
