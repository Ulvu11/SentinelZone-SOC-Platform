"""Tenant isolation for ORM operations; tenant comes from verified identity, never request input.

Core SQL is restricted to migrations/backup/authentication. Application data access uses ORM.
A session may bind to one authenticated tenant before data access and must not be reused
for a different tenant. Composite foreign keys provide an additional database boundary.
"""
from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session, with_loader_criteria
from app.db.models import TenantScoped, EventSet, AssetSnapshot


def tenant_id(session) -> str:
    from app.config import get_settings
    return session.info.get("tenant_id", get_settings().default_tenant_id)


def bind_tenant(session, value: str):
    if session.info.get("tenant_bound") and tenant_id(session) != value:
        raise ValueError("A session cannot switch tenants")
    session.info.update(tenant_id=value, tenant_bound=True)


def scoped_get(session, model, identity):
    keys = [c for c in inspect(model).primary_key if c.key != "tenant_id"]
    vals = identity if isinstance(identity, tuple) else (identity,)
    if len(keys) != len(vals):
        raise ValueError("Invalid scoped identity")
    q = select(model).where(model.tenant_id == tenant_id(session))
    for col, val in zip(keys, vals):
        q = q.where(col == val)
    return session.scalar(q)


@event.listens_for(Session, "do_orm_execute")
def _scope(execute_state):
    mapper = execute_state.bind_mapper
    if execute_state.is_insert and mapper is not None and issubclass(mapper.class_, TenantScoped):
        params = execute_state.parameters
        if params is None:
            raise ValueError("Use ORM add() or explicit parameter dictionaries for tenant-scoped inserts")
        for values in params if isinstance(params, list) else [params]:
            expected = tenant_id(execute_state.session)
            if values.get("tenant_id", expected) != expected:
                raise ValueError("Cross-tenant bulk insert denied")
            values["tenant_id"] = expected
    if execute_state.is_update and mapper is not None and issubclass(mapper.class_, TenantScoped):
        if "tenant_id" in execute_state.statement.compile().params:
            raise ValueError("Tenant identity is immutable")
    if execute_state.is_select or execute_state.is_update or execute_state.is_delete:
        tid = tenant_id(execute_state.session)
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(TenantScoped, lambda cls: cls.tenant_id == tid, include_aliases=True)
        )
    if execute_state.is_update or execute_state.is_delete:
        mapper = execute_state.bind_mapper
        if mapper is not None and mapper.class_ in (EventSet, AssetSnapshot):
            raise ValueError("Stored snapshots are immutable")


@event.listens_for(Session, "before_flush")
def _check_tenant(session, flush_context, instances):
    tid = tenant_id(session)
    for obj in session.new | session.dirty | session.deleted:
        if isinstance(obj, TenantScoped):
            if obj in session.new and obj.tenant_id is None:
                obj.tenant_id = tid
            if obj.tenant_id != tid:
                raise ValueError("Cross-tenant write denied")
            state = inspect(obj)
            if obj not in session.new and state.attrs.tenant_id.history.has_changes():
                raise ValueError("Tenant identity is immutable")
        if isinstance(obj, (EventSet, AssetSnapshot)) and obj not in session.new:
            if obj in session.deleted or session.is_modified(obj, include_collections=True):
                raise ValueError("Stored snapshots are immutable")
        # Defaults must be set before constructing composite foreign keys.
        if hasattr(obj, "execution_mode") and getattr(obj, "execution_mode") is None:
            obj.execution_mode = "TEST" if getattr(obj, "is_test", False) else "REAL"
