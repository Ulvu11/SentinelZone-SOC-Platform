import hashlib
import secrets

from sqlalchemy import select

from app.auth.roles import PERMISSIONS, ROLES
from app.db.models import AuditLog, Role, User


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def seed_roles(session) -> None:
    existing = {r.name for r in session.scalars(select(Role))}
    for name, perms in PERMISSIONS.items():
        if name not in existing:
            session.add(Role(name=name, permissions=sorted(perms)))
    session.flush()


def create_user(session, username: str, role: str, actor: str) -> str:
    """Returns the plaintext token ONCE; only its SHA-256 is stored."""
    if role not in ROLES:
        raise ValueError("invalid role")
    if session.scalar(select(User).where(User.username == username)):
        raise KeyError("username exists")
    seed_roles(session)
    token = secrets.token_urlsafe(32)
    session.add(User(username=username, role=role, token_hash=hash_token(token), is_active=True))
    session.add(AuditLog(actor=actor, action="USER_CREATED", detail={"username": username, "role": role}))
    session.flush()
    return token


def rotate_token(session, username: str, actor: str) -> str:
    u = session.scalar(select(User).where(User.username == username))
    if u is None:
        raise LookupError(username)
    token = secrets.token_urlsafe(32)
    u.token_hash = hash_token(token)
    session.add(AuditLog(actor=actor, action="USER_TOKEN_ROTATED", detail={"username": username}))
    session.flush()
    return token


def find_by_token(session, token: str):
    # The only cross-tenant lookup: fixed SQL by a globally unique SHA-256 token.
    # Core mappings avoid populating another tenant's ORM identity map.
    from types import SimpleNamespace
    row = session.connection().execute(
        User.__table__.select().where(User.__table__.c.token_hash == hash_token(token), User.__table__.c.is_active.is_(True))
    ).mappings().first()
    return SimpleNamespace(**row) if row else None
