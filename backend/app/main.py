
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.exc import StaleDataError

from app import __version__
from app.config import get_settings
from app.scheduler import lifespan
from app.api import cryptoguard
from app.api import reports
from app.api import investigations, action_proposals, admin, agents, alerts, assets, health, hunts, incidents, merge_requests, notifications, overview, telemetry


def create_app(settings=None) -> FastAPI:
    settings = (settings or get_settings()).validate_runtime()
    app = FastAPI(title="SentinelZone Backend", version=__version__,
                  description="Unified SOC backend: Phase 24 (API), 26 (Incidents), 27 (Notifications)", lifespan=lifespan)
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=settings.cors_allow_credentials, allow_methods=["*"], allow_headers=["*"])
    for mod in (investigations, health, alerts, overview, assets, agents, telemetry, incidents, merge_requests, notifications, hunts, admin, action_proposals):
        app.include_router(mod.router)

    app.state.settings = settings
    app.include_router(cryptoguard.router)
    app.include_router(reports.router)
    app.dependency_overrides[get_settings] = lambda: settings
    if settings.app_env == "development" and settings.enable_legacy_mock_routes:
        from app.routers.core import router as mock_router
        app.include_router(mock_router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"service": "Unified SOC API", "docs": "/docs"}

    @app.exception_handler(StaleDataError)
    async def _stale(_: Request, __):
        return JSONResponse(status_code=409, content={"detail": {"message": "concurrent modification"}})

    @app.exception_handler(OperationalError)
    async def _db_down(_: Request, __):
        return JSONResponse(status_code=503, content={"detail": "database unavailable"})

    return app


app = create_app()
