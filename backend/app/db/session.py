from functools import lru_cache
from fastapi import Depends
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.config import get_settings,Settings


@lru_cache(maxsize=8)
def _database(url):
    kwargs={"pool_pre_ping":True}
    if url.startswith("sqlite"):
        kwargs["connect_args"]={"check_same_thread":False}
    engine=create_engine(url,**kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine,"connect")
        def constraints(connection,_):
            connection.execute("PRAGMA foreign_keys=ON")
    return engine,sessionmaker(bind=engine,expire_on_commit=False)


def get_engine(settings=None):
    settings=(settings or get_settings()).validate_runtime()
    return _database(settings.database_url)[0]


def get_session_factory(settings=None):
    settings=(settings or get_settings()).validate_runtime()
    return _database(settings.database_url)[1]


def get_db(settings:Settings=Depends(get_settings)):
    """Request session: default tenant first, then bound to verified identity before endpoint execution."""
    db=get_session_factory(settings)(info={"tenant_id":settings.default_tenant_id})
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
