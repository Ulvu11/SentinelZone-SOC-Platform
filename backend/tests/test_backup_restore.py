import asyncio
import os
import shutil

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backup import backup_and_verify
from app.connectors.cryptoguard import build_connectors
from app.db.models import Base
from app.ingest import run_ingest


def test_backup_then_restore_matches_live_data(tmp_path, settings):
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path}/live.db"
    if url.startswith("postgresql") and not (os.environ.get("PG_BIN") or shutil.which("pg_dump")):
        pytest.skip("pg_dump/pg_restore not available")
    eng = create_engine(url)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    s = sessionmaker(bind=eng)()
    asyncio.run(run_ingest(s, settings, build_connectors(settings)))
    s.commit()
    s.close()
    eng.dispose()
    res = backup_and_verify(url, str(tmp_path / "bk"))
    assert res["ok"] is True
    assert res["live"]["events"] == 6 and res["restored"]["events"] == 6
    assert res["restored"]["incidents"] == 1 and res["restored"]["notifications"] >= 2
