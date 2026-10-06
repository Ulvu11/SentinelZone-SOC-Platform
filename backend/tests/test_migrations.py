import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.db.models import Base

ROOT = Path(__file__).resolve().parent.parent


def test_migrations_upgrade_match_models_and_downgrade(tmp_path, monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path}/mig.db"
    eng = create_engine(url)
    Base.metadata.drop_all(eng)
    with eng.begin() as c:
        c.execute(text("DROP TABLE IF EXISTS alembic_version"))
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    try:
        command.upgrade(cfg, "head")
        command.check(cfg)  # raises if models and migrations disagree
        with eng.connect() as c:
            assert c.execute(text("select count(*) from roles")).scalar() == 4
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")  # re-applies cleanly
        command.downgrade(cfg, "base")
    finally:
        eng.dispose()
        monkeypatch.undo()
        get_settings.cache_clear()
