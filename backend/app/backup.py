"""Backup -> restore into a scratch database -> compare row counts. Never touches the live database."""
import os
import shutil
import sqlite3
import subprocess
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.db.models import Base

CHECK_TABLES = sorted(Base.metadata.tables)


def _counts(url) -> dict:
    eng = create_engine(url)
    try:
        with eng.connect() as c:
            return {t: c.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in CHECK_TABLES}
    finally:
        eng.dispose()


def _pg_bin(name: str) -> str:
    base = os.environ.get("PG_BIN")
    path = str(Path(base, name)) if base else shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} not found (install postgresql-client or set PG_BIN)")
    return path


def backup_and_verify(database_url: str, workdir: str) -> dict:
    url = make_url(database_url)
    Path(workdir).mkdir(parents=True, exist_ok=True)
    live = _counts(url)
    if url.get_backend_name() == "sqlite":
        src, dst = url.database, str(Path(workdir, "backup.db"))
        if Path(src).resolve() == Path(dst).resolve():
            raise ValueError("Backup target must differ from source")
        a, b = sqlite3.connect(src), sqlite3.connect(dst)
        a.backup(b)
        a.close(); b.close()
        restored = _counts(f"sqlite:///{dst}")
        return {"engine": "sqlite", "live": live, "restored": restored, "ok": live == restored}
    host = url.query.get("host") or url.host or "localhost"
    env = {**os.environ, "PGPASSWORD": url.password or ""}
    base = ["-h", host, "-p", str(url.port or 5432), "-U", url.username or "postgres"]
    dump = str(Path(workdir, "backup.dump"))
    scratch = "sz_restore_verify_" + uuid.uuid4().hex
    created = False
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        subprocess.run([_pg_bin("pg_dump"), *base, "-Fc", "-f", dump, url.database], check=True, env=env, capture_output=True)
        with admin.connect() as c:
            c.execute(text(f'CREATE DATABASE "{scratch}"'))
            created = True
        subprocess.run([_pg_bin("pg_restore"), *base, "-d", scratch, "--no-owner", dump], check=True, env=env, capture_output=True)
        restored = _counts(url.set(database=scratch))
        return {"engine": "postgresql", "live": live, "restored": restored, "ok": live == restored}
    finally:
        if created:
            with admin.connect() as c:
                c.execute(text(f'DROP DATABASE "{scratch}"'))
        admin.dispose()
