"""Tenant/mode isolation, sensor health, immutable investigation snapshots.

Revision ID: 0003
Revises: 0002
Legacy rows are assigned to DEFAULT_TENANT_ID (lab by default).
A mixed historical REAL/TEST incident must be reconciled before migration;
this is checked before any schema mutations. No historical evidence is deleted.
"""
import os
import re
import sqlalchemy as sa
from alembic import op

revision="0003"
down_revision="0002"
branch_labels=None
depends_on=None
NAMING={"pk":"pk_%(table_name)s", "fk":"fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "uq":"uq_%(table_name)s_%(column_0_name)s", "ck":"ck_%(table_name)s_%(constraint_name)s"}


def _constraints_off(bind,tables):
    # Remove inbound FKs before changing referenced keys; batch mode supports SQLite.
    for name in tables:
        fks=sa.inspect(bind).get_foreign_keys(name)
        if not fks:continue
        with op.batch_alter_table(name,naming_convention=NAMING) as b:
            for fk in fks:
                cname=fk["name"] or f"fk_{name}_{fk['constrained_columns'][0]}_{fk['referred_table']}"
                b.drop_constraint(cname,type_="foreignkey")


def _shape(bind,metadata,upgrade):
    from migrations.schema_0002 import Base as OldBase
    from migrations.schema_0003 import Base as NewBase
    managed=set(OldBase.metadata.tables)|set(NewBase.metadata.tables)
    existing=set(sa.inspect(bind).get_table_names()) & managed
    # Never drop/rewrite unrelated tables or their constraints in a shared DB.
    _constraints_off(bind,sorted(existing))
    # Child tables have no foreign keys now.
    for name in sorted(existing-set(metadata.tables)):
        op.drop_table(name)
    for table in metadata.sorted_tables:
        name=table.name
        if name not in existing:
            # New table FKs are added in the common final pass.
            copy_meta=sa.MetaData()
            copied=table.to_metadata(copy_meta)
            for constraint in list(copied.foreign_key_constraints):
                copied.constraints.remove(constraint)
            copied.create(bind)
            continue
        inspector=sa.inspect(bind)
        old_cols={c["name"] for c in inspector.get_columns(name)}
        old_pk=inspector.get_pk_constraint(name)
        new_pk=[c.name for c in table.primary_key.columns]
        # Drop old UQ/checks before removing columns or changing scopes.
        with op.batch_alter_table(name,naming_convention=NAMING) as b:
            for c in inspector.get_unique_constraints(name):
                b.drop_constraint(c["name"] or f"uq_{name}_{c['column_names'][0]}",type_="unique")
            for c in inspector.get_check_constraints(name):
                cname=c["name"]
                if cname:
                    # Reflected named checks may be decorated by the naming convention.
                    # SQLite reflection decorates names during batch recreation;
                    # PostgreSQL ALTER TABLE must use the real, unmodified name.
                    b.drop_constraint(op.f(cname) if bind.dialect.name == "postgresql" else cname,type_="check")
            for col in table.columns:
                if col.name not in old_cols:
                    b.add_column(sa.Column(col.name,col.type,nullable=col.nullable,server_default=col.server_default))
        if upgrade:
            tenant=os.environ.get("DEFAULT_TENANT_ID","lab")
            if "tenant_id" in table.c:
                bind.execute(sa.text(f'UPDATE "{name}" SET tenant_id = :tenant'),{"tenant":tenant})
            if name=="events":
                bind.execute(sa.text("UPDATE events SET execution_mode = CASE WHEN is_test THEN 'TEST' ELSE 'REAL' END"))
            if name=="incidents":
                bind.execute(sa.text("UPDATE incidents SET updated_at = last_seen, summary = title"))
        with op.batch_alter_table(name,naming_convention=NAMING) as b:
            for index in sa.inspect(bind).get_indexes(name):
                if index.get("duplicates_constraint"):
                    continue  # PostgreSQL constraint-owned indexes are not separate indexes.
                if any(c not in table.c for c in index["column_names"]):
                    b.drop_index(index["name"])
            if old_pk["constrained_columns"]!=new_pk:
                b.drop_constraint(old_pk["name"] or f"pk_{name}",type_="primary")
            for col in old_cols-set(table.c.keys()):
                b.drop_column(col)
            if old_pk["constrained_columns"]!=new_pk:
                b.create_primary_key(f"pk_{name}",new_pk)
            for c in table.constraints:
                if isinstance(c,sa.UniqueConstraint):
                    b.create_unique_constraint(c.name or f"uq_{name}_{list(c.columns)[0].name}",[x.name for x in c.columns])
                elif isinstance(c,sa.CheckConstraint):
                    b.create_check_constraint(op.f(c.name),c.sqltext)
        existing_indexes={c["name"] for c in sa.inspect(bind).get_indexes(name)}
        for index in table.indexes:
            if index.name not in existing_indexes:
                op.create_index(index.name,name,[c.name for c in index.columns],unique=index.unique)
    if upgrade:
        for name in ("external_refs","incident_candidates","incident_events"):
            bind.execute(sa.text(f"UPDATE {name} SET execution_mode = (SELECT execution_mode FROM events WHERE events.event_uid = {name}.event_uid AND events.tenant_id = {name}.tenant_id)"))
        bind.execute(sa.text("UPDATE incidents SET execution_mode = 'TEST' WHERE EXISTS (SELECT 1 FROM incident_events l WHERE l.incident_id = incidents.id AND l.execution_mode = 'TEST')"))
        bind.execute(sa.text("UPDATE notifications SET status='SUPPRESSED', suppression_reason='POLICY_DENIED' WHERE channel != 'dashboard' AND status='PENDING' AND incident_id IN (SELECT id FROM incidents WHERE execution_mode='TEST')"))
    for table in metadata.sorted_tables:
        fks=list(table.foreign_key_constraints)
        if not fks:continue
        with op.batch_alter_table(table.name,naming_convention=NAMING) as b:
            for fk in fks:
                elements=list(fk.elements)
                b.create_foreign_key(fk.name or f"fk_{table.name}_{elements[0].parent.name}_{elements[0].column.table.name}",
                    elements[0].column.table.name,[e.parent.name for e in elements],[e.column.name for e in elements])


def _immutable_triggers(bind,create):
    for table in ("event_sets","asset_snapshots"):
        if bind.dialect.name=="postgresql":
            if create:
                op.execute(sa.text(f"CREATE FUNCTION deny_{table}_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'snapshot is immutable'; END $$"))
                op.execute(sa.text(f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION deny_{table}_mutation()"))
            else:
                op.execute(sa.text(f"DROP TRIGGER IF EXISTS immutable_{table} ON {table}"))
                op.execute(sa.text(f"DROP FUNCTION IF EXISTS deny_{table}_mutation()"))
        elif bind.dialect.name=="sqlite":
            for verb in ("UPDATE","DELETE"):
                name=f"immutable_{table}_{verb.lower()}"
                if create:op.execute(sa.text(f"CREATE TRIGGER {name} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT, 'snapshot is immutable'); END"))
                else:op.execute(sa.text(f"DROP TRIGGER IF EXISTS {name}"))


def upgrade():
    bind=op.get_bind()
    tenant=os.environ.get("DEFAULT_TENANT_ID","lab")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",tenant):
        raise RuntimeError("Invalid DEFAULT_TENANT_ID")
    mixed=bind.execute(sa.text("SELECT l.incident_id FROM incident_events l JOIN events e ON e.event_uid=l.event_uid GROUP BY l.incident_id HAVING MIN(CASE WHEN e.is_test THEN 1 ELSE 0 END) <> MAX(CASE WHEN e.is_test THEN 1 ELSE 0 END)")).first()
    if mixed:
        raise RuntimeError("Mixed historical REAL/TEST incident: reconcile evidence before upgrading; no schema changes performed")
    from migrations.schema_0003 import Base
    _shape(bind,Base.metadata,True)
    _immutable_triggers(bind,True)
    roles = sa.table("roles", sa.column("name",sa.String), sa.column("permissions",sa.JSON))
    # This revision introduces replay authorization. Freeze the values here.
    for role in ("analyst","operator","admin"):
        perms=bind.execute(sa.select(roles.c.permissions).where(roles.c.name==role)).scalar()
        if perms is not None:
            bind.execute(roles.update().where(roles.c.name==role).values(permissions=sorted(set(perms)|{"replay"})))


def downgrade():
    bind=op.get_bind()
    # Old schema cannot represent colliding native IDs across tenants or modes.
    for table,key in (("events","event_uid"),("assets","host_id"),("connector_state","source"),("users","username")):
        if bind.execute(sa.text(f'SELECT "{key}" FROM "{table}" GROUP BY "{key}" HAVING count(*) > 1')).first():
            raise RuntimeError("Downgrade would collapse tenant/mode identities; export and reconcile first")
    _immutable_triggers(bind,False)
    from migrations.schema_0002 import Base
    _shape(bind,Base.metadata,False)
