from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.permissions import require
from app.db.models import Asset, AuditLog
from app.db.session import get_db
from app.db.tenancy import scoped_get

router = APIRouter(prefix="/v1", tags=["assets"])


def _out(a: Asset) -> dict:
    return {"host_id": a.host_id, "agent_id": a.agent_id, "agent_ip": a.agent_ip, "role": a.role, "tenant_id":a.tenant_id, "criticality":a.criticality,
            "first_seen": a.first_seen, "last_seen": a.last_seen, "sources": a.sources or []}


def _page(db, q, limit, cursor):
    if cursor:
        q = q.where(Asset.host_id > cursor)
    rows = list(db.scalars(q.order_by(Asset.host_id).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit]
    return {"items": [_out(a) for a in rows], "next_cursor": rows[-1].host_id if more and rows else None}


@router.get("/assets")
def assets(limit: int = Query(100, ge=1, le=500), cursor: str | None = None, db=Depends(get_db), _=Depends(require("read"))):
    return _page(db, select(Asset), limit, cursor)



class AssetPatch(BaseModel):
    role: str | None = None  # e.g. splunk, wazuh-manager, pfsense, domain-controller, backup, admin-host (protected roles)


@router.patch("/assets/{host_id}")
def patch_asset(host_id: str, body: AssetPatch, db=Depends(get_db), p=Depends(require("admin"))):
    a = scoped_get(db, Asset, host_id)
    if a is None:
        raise HTTPException(404, "asset not found")
    db.add(AuditLog(actor=p.name, action="ASSET_ROLE_SET", detail={"host_id": host_id, "role": body.role}))
    a.role = body.role
    db.commit()
    return _out(a)
