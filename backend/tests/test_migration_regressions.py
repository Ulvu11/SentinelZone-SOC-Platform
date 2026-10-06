from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine,select,text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.config import get_settings
from app.db.models import Event,Incident,Notification,EventSet
from app.incidents.replay import canonical_hash
from tests.conftest import mk_event,T0


def test_migration_preserves_unrelated_tables_and_constraints(tmp_path,monkeypatch):
    from sqlalchemy import inspect
    cfg,e=setup_migration(tmp_path,monkeypatch)
    try:
        with e.begin() as c:
            c.execute(text("CREATE TABLE unrelated_parent (id INTEGER PRIMARY KEY)"))
            c.execute(text("CREATE TABLE unrelated_child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES unrelated_parent(id))"))
            c.execute(text("INSERT INTO unrelated_parent VALUES (7)"))
            c.execute(text("INSERT INTO unrelated_child VALUES (8,7)"))
        for revision in ("head","0002","head"):
            command.upgrade(cfg,revision) if revision=="head" else command.downgrade(cfg,revision)
            with e.connect() as c:
                assert c.execute(text("SELECT parent_id FROM unrelated_child WHERE id=8")).scalar()==7
            assert inspect(e).get_foreign_keys("unrelated_child")[0]["referred_table"]=="unrelated_parent"
    finally:e.dispose();get_settings.cache_clear()


def setup_migration(tmp_path,monkeypatch):
    url=f"sqlite:///{tmp_path}/migration.db"
    monkeypatch.setenv("DATABASE_URL",url);get_settings.cache_clear()
    cfg=Config(str(Path(__file__).resolve().parents[1]/"alembic.ini"))
    command.upgrade(cfg,"0002")
    return cfg,create_engine(url)


def seed_old(engine,test=False,mixed=False,uid="legacy"):
    from migrations.schema_0002 import Event as OE, Incident as OI,IncidentEvent as OL,Notification as ON
    with Session(engine) as s:
        data=mk_event(uid,is_test=test).model_dump(exclude={"tenant_id","execution_mode"})
        s.add(OE(**data));s.flush()
        i=OI(opened_at=T0,last_seen=T0,status="NEW",priority="high",host_id="HOST1",title="old incident")
        s.add(i);s.flush();s.add(OL(incident_id=i.id,event_uid=uid))
        s.add(ON(incident_id=i.id,incident_version=1,channel="telegram",status="PENDING",idempotency_key=f"old:{uid}",payload={}))
        if mixed:
            data=mk_event("legacy-test",is_test=True).model_dump(exclude={"tenant_id","execution_mode"})
            s.add(OE(**data));s.flush();s.add(OL(incident_id=i.id,event_uid="legacy-test"))
        s.commit()


@pytest.mark.parametrize("is_test",[False,True])
def test_migration_preserves_legacy_data(tmp_path,monkeypatch,is_test):
    cfg,e=setup_migration(tmp_path,monkeypatch)
    try:
        seed_old(e,test=is_test)
        command.upgrade(cfg,"head");command.check(cfg)
        with Session(e) as s:
            ev=s.scalar(select(Event));inc=s.scalar(select(Incident));n=s.scalar(select(Notification))
            assert ev.event_uid=="legacy" and ev.tenant_id=="lab"
            assert ev.execution_mode==inc.execution_mode==("TEST" if is_test else "REAL")
            assert inc.summary=="old incident" and inc.updated_at==T0
            assert n.status==("SUPPRESSED" if is_test else "PENDING")
            assert n.template_version=="1"
    finally:e.dispose();get_settings.cache_clear()


def test_migration_rejects_mixed_historical_incident_before_changes(tmp_path,monkeypatch):
    cfg,e=setup_migration(tmp_path,monkeypatch)
    try:
        seed_old(e,mixed=True)
        with pytest.raises(RuntimeError,match="Mixed historical"):
            command.upgrade(cfg,"head")
        with e.connect() as c:
            assert c.execute(text("SELECT version_num FROM alembic_version")).scalar()=="0002"
        from sqlalchemy import inspect
        assert "tenant_id" not in {c["name"] for c in inspect(e).get_columns("events")}
    finally:e.dispose();get_settings.cache_clear()


def test_event_set_database_immutability(tmp_path,monkeypatch):
    cfg,e=setup_migration(tmp_path,monkeypatch)
    try:
        command.upgrade(cfg,"head")
        with Session(e) as s:
            s.add(EventSet(id="immutable",content_hash=canonical_hash([]),events=[],created_by="test"));s.commit()
        with e.begin() as c:
            with pytest.raises(IntegrityError,match="immutable"):
                c.execute(text("UPDATE event_sets SET events='[]' WHERE id='immutable'"))
        with e.begin() as c:
            with pytest.raises(IntegrityError,match="immutable"):
                c.execute(text("DELETE FROM event_sets WHERE id='immutable'"))
    finally:e.dispose();get_settings.cache_clear()
