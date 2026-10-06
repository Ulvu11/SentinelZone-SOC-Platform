from fastapi import APIRouter, Depends, HTTPException

from app.auth.permissions import require
from app.config import Settings, get_settings
from app.connectors.cryptoguard import build_connectors
from app.db.session import get_db
from app.ingest import run_ingest, try_ingest_lock

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/ingest/run")
async def ingest_run(db=Depends(get_db), p=Depends(require("admin")), settings: Settings = Depends(get_settings)):
    if p.tenant_id != settings.default_tenant_id:
        raise HTTPException(403, "Connector configuration belongs to a different tenant")
    if not try_ingest_lock(db):
        raise HTTPException(409, "another ingest run is already in progress")
    result = await run_ingest(db, settings, build_connectors(settings))
    db.commit()
    return result


from pydantic import BaseModel  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.auth import users as user_svc  # noqa: E402
from app.auth.roles import PERMISSIONS  # noqa: E402
from app.db.models import AuditLog, Role, User  # noqa: E402


class UserIn(BaseModel):
    username: str
    role: str


class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None


def _u(u: User) -> dict:
    return {"username": u.username, "role": u.role, "is_active": u.is_active, "created_at": u.created_at}


@router.get("/users")
def list_users(db=Depends(get_db), _=Depends(require("admin"))):
    return {"items": [_u(u) for u in db.scalars(select(User).order_by(User.username))]}


@router.post("/users", status_code=201)
def create_user(body: UserIn, db=Depends(get_db), p=Depends(require("admin"))):
    if not (3 <= len(body.username) <= 64):
        raise HTTPException(422, "username must be 3-64 chars")
    try:
        token = user_svc.create_user(db, body.username, body.role, p.name)
    except ValueError:
        raise HTTPException(422, f"role must be one of {sorted(PERMISSIONS)}")
    except KeyError:
        raise HTTPException(409, "username already exists")
    db.commit()
    return {"username": body.username, "role": body.role, "token": token, "note": "store this token now; it is not shown again"}


@router.patch("/users/{username}")
def patch_user(username: str, body: UserPatch, db=Depends(get_db), p=Depends(require("admin"))):
    u = db.scalar(select(User).where(User.username == username))
    if u is None:
        raise HTTPException(404, "user not found")
    if body.role is not None:
        if body.role not in PERMISSIONS:
            raise HTTPException(422, f"role must be one of {sorted(PERMISSIONS)}")
        u.role = body.role
    if body.is_active is not None:
        u.is_active = body.is_active
    db.add(AuditLog(actor=p.name, action="USER_UPDATED", detail={"username": username, **body.model_dump(exclude_none=True)}))
    db.commit()
    return _u(u)


@router.post("/users/{username}/rotate-token")
def rotate(username: str, db=Depends(get_db), p=Depends(require("admin"))):
    try:
        token = user_svc.rotate_token(db, username, p.name)
    except LookupError:
        raise HTTPException(404, "user not found")
    db.commit()
    return {"username": username, "token": token}


@router.get("/roles")
def list_roles(db=Depends(get_db), _=Depends(require("admin"))):
    user_svc.seed_roles(db)
    db.commit()
    return {"items": [{"name": r.name, "permissions": r.permissions} for r in db.scalars(select(Role).order_by(Role.name))]}
