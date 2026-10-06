from fastapi import APIRouter
from app.schemas.models import Endpoint, Incident, Overview
from app.services.mock_data import ENDPOINTS, INCIDENTS, OVERVIEW

router = APIRouter(prefix="/api")

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/overview", response_model=Overview)
def overview() -> Overview:
    return OVERVIEW

@router.get("/incidents", response_model=list[Incident])
def incidents() -> list[Incident]:
    return INCIDENTS

@router.get("/endpoints", response_model=list[Endpoint])
def endpoints() -> list[Endpoint]:
    return ENDPOINTS
