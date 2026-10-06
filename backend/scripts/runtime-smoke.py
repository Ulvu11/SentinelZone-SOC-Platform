"""Launch real Uvicorn on loopback with a fresh temporary SQLite DB; no upstream calls."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import Settings


def main():
    env = {k: v for k, v in os.environ.items() if k.lower() not in Settings.model_fields}
    env.update(APP_ENV="development", PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
    result = {"database": "temporary SQLite", "live_connectors": "UNVERIFIED"}
    with tempfile.TemporaryDirectory(prefix="sentinelzone-http-") as tmp:
        env["DATABASE_URL"] = f"sqlite:///{tmp}/http.db"
        migrate = subprocess.run([sys.executable, "-m", "alembic", "-c", str(ROOT / "alembic.ini"), "upgrade", "head"],
                                 cwd=tmp, env=env, capture_output=True, text=True)
        assert migrate.returncode == 0, migrate.stderr
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        with tempfile.TemporaryFile(mode="w+") as log:
            server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                                       "--fd", str(listener.fileno()), "--no-access-log"],
                                      cwd=tmp, env=env, pass_fds=(listener.fileno(),), stdout=log, stderr=log)
            listener.close()
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                origin = f"http://127.0.0.1:{port}"
                deadline = time.monotonic() + 15
                while True:
                    try:
                        with opener.open(origin + "/health", timeout=1) as response:
                            health = json.load(response)
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if server.poll() is not None or time.monotonic() > deadline:
                            raise AssertionError("Uvicorn did not become ready")
                        time.sleep(0.1)
                assert health["database"] == "healthy"
                assert health["status"] == "degraded"
                assert set(health["connectors"].values()) == {"not_configured"}
                result["health"] = {"http_status": 200, **health}
                result["routes"] = {}
                for path, expected in (("/api/overview", 404), ("/api/incidents", 404),
                                       ("/api/endpoints", 404), ("/v1/alerts", 401)):
                    try:
                        with opener.open(origin + path, timeout=3) as response:
                            status = response.status
                    except urllib.error.HTTPError as exc:
                        status = exc.code
                    assert status == expected, (path, status)
                    result["routes"][path] = status
                with opener.open(origin + "/openapi.json", timeout=3) as response:
                    contract = json.load(response)
                assert contract == json.loads((ROOT / "docs/openapi.json").read_text())
                result["openapi"] = {"matches_saved": True, "paths": len(contract["paths"])}
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
        invalid = subprocess.run([sys.executable, "-c", "import app.main"], cwd=tmp,
                                 env={**env, "APP_ENV": "production"}, capture_output=True, text=True)
        assert invalid.returncode != 0 and "DATABASE_URL must be PostgreSQL in production" in invalid.stderr
        result["production_sqlite_startup"] = "REJECTED"
    result["status"] = "PASS"
    output = json.dumps(result, indent=2) + "\n"
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports/runtime-smoke.json").write_text(output)
    print(output)


if __name__ == "__main__":
    main()
