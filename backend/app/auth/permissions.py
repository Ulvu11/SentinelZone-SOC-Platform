import hmac
import re
from app.db.tenancy import bind_tenant

from fastapi import Depends, Header, HTTPException

from app.auth.roles import ROLES, Principal
from app.auth.users import find_by_token
from app.config import Settings, get_settings
from app.db.session import get_db


def parse_tokens(raw: str, default_tenant: str = "lab") -> list[tuple[str, Principal]]:
    out = []
    for item in filter(None, (x.strip() for x in raw.split(";"))):
        parts = item.split(":")
        if len(parts) in (3, 4) and parts[2] in ROLES and parts[0] and parts[1]:
            tenant = parts[3] if len(parts) == 4 else default_tenant
            if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", tenant):
                out.append((parts[0], Principal(parts[1], parts[2], tenant)))
    return out


def get_principal(authorization: str | None = Header(default=None), settings: Settings = Depends(get_settings), db=Depends(get_db)) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token", headers={"WWW-Authenticate": "Bearer"})
    supplied = authorization[7:].strip()
    for token, principal in parse_tokens(settings.auth_tokens, settings.default_tenant_id):
        if hmac.compare_digest(token, supplied):
            bind_tenant(db, principal.tenant_id)
            return principal
    user = find_by_token(db, supplied) if settings.auth_db_enabled else None  # DB users (hashed tokens, can be disabled/rotated)
    if user and user.role in ROLES:
        bind_tenant(db, user.tenant_id)
        return Principal(user.username, user.role, user.tenant_id)
    raise HTTPException(401, "invalid token", headers={"WWW-Authenticate": "Bearer"})


def require(perm: str):
    def dep(p: Principal = Depends(get_principal)) -> Principal:
        if not p.can(perm):
            raise HTTPException(403, f"role '{p.role}' lacks permission '{perm}'")
        return p
    return dep
