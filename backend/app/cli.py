"""python -m app.cli [ingest|dispatch|seed-roles|create-user <name> <role>|backup-verify [dir]]"""
import asyncio
import sys
import tempfile

from app.config import get_settings
from app.connectors.cryptoguard import build_connectors
from app.db.session import get_session_factory
from app.ingest import run_ingest, try_ingest_lock
from app.notifications.outbox import dispatch_due
from app.notifications.senders import build_senders


def main(argv):
    s = get_settings().validate_runtime()
    cmd = argv[0] if argv else ""
    if cmd == "backup-verify":
        from app.backup import backup_and_verify

        res = backup_and_verify(s.database_url, argv[1] if len(argv) > 1 else tempfile.mkdtemp(prefix="sz-backup-"))
        print(res)
        return 0 if res["ok"] else 1
    if cmd not in ("ingest", "dispatch", "seed-roles", "create-user"):
        print(__doc__)
        return 2
    db = get_session_factory(s)(info={"tenant_id":s.default_tenant_id})
    try:
        if cmd == "ingest":
            if not try_ingest_lock(db):
                print("another ingest is running")
                return 3
            print(asyncio.run(run_ingest(db, s, build_connectors(s))))
        elif cmd == "dispatch":
            tg, sms = build_senders(s)
            print(dispatch_due(db, s, tg, sms_sender=sms))
        elif cmd == "seed-roles":
            from app.auth.users import seed_roles

            seed_roles(db)
            print("roles seeded")
        elif cmd == "create-user":
            from app.auth.users import create_user

            print("TOKEN (shown once):", create_user(db, argv[1], argv[2], "cli"))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
