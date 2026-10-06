from fastapi import APIRouter, Depends, HTTPException

from app.auth.permissions import require
from app.config import Settings, get_settings
from app.connectors.base import ConnectorError
from app.connectors.splunk import APPROVED_HUNTS, SplunkConnector

router = APIRouter(prefix="/v1/hunts", tags=["hunts"])


@router.post("/{approved_query_id}/run")
async def run_hunt(approved_query_id: str, p=Depends(require("hunt")), settings: Settings = Depends(get_settings)):
    if p.tenant_id != settings.default_tenant_id:
        raise HTTPException(403, "Connector configuration belongs to a different tenant")
    if approved_query_id not in APPROVED_HUNTS:  # only allowlisted queries; never free-form SPL
        raise HTTPException(404, "unknown approved query")
    try:
        return await SplunkConnector(settings).run_hunt(approved_query_id)
    except ConnectorError as e:
        raise HTTPException(503, f"splunk unavailable: {e}")
