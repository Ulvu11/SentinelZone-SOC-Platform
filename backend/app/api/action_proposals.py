"""Phase 29 SKELETON ONLY. No executor exists: approving a proposal changes state, nothing else."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.auth.permissions import require
from app.config import Settings, get_settings
from app.db.models import ActionProposal, Asset, utcnow
from app.db.session import get_db
from app.db.tenancy import scoped_get
from app.incidents import service
from app.incidents.models import NotFound
from app.schemas import ProposalIn

router = APIRouter(prefix="/v1/action-proposals", tags=["action-proposals"])

# Allowed state machine for a future executor; this skeleton itself only performs PENDING_APPROVAL -> APPROVED/REJECTED/EXPIRED.
TRANSITIONS = {
    "PROPOSED": {"PENDING_APPROVAL"},
    "PENDING_APPROVAL": {"APPROVED", "REJECTED", "EXPIRED"},
    "APPROVED": {"EXECUTING", "EXPIRED"},
    "EXECUTING": {"SUCCESS", "FAILED"},
    "FAILED": {"ROLLED_BACK"},
    "SUCCESS": {"ROLLED_BACK"},
    "REJECTED": set(), "EXPIRED": set(), "ROLLED_BACK": set(),
}
STATES = list(TRANSITIONS)


def _out(p: ActionProposal) -> dict:
    return {"proposal_id": f"ACT-{p.id:06d}", "incident_id": f"SZ-{p.incident_id:06d}", "action_type": p.action_type,
            "target": p.target, "status": p.status, "proposed_by": p.proposed_by, "decided_by": p.decided_by, "expires_at": p.expires_at}


def _csv(v: str) -> set[str]:
    return {x.strip() for x in v.split(",") if x.strip()}


def is_protected(db, target: str, settings: Settings) -> bool:
    """Protected = listed in PROTECTED_TARGETS (hostname or IP), or its asset has a protected role
    (Splunk, Wazuh manager, pfSense, domain controllers, backup, admin hosts)."""
    if target in _csv(settings.protected_targets):
        return True
    a = db.scalar(select(Asset).where((Asset.host_id == target) | (Asset.agent_ip == target)))
    if a is None:
        return False
    return a.host_id in _csv(settings.protected_targets) or (a.agent_ip or "") in _csv(settings.protected_targets) \
        or (a.role or "") in _csv(settings.protected_asset_roles)


def _sweep_expired(db):
    for pr in db.scalars(select(ActionProposal).where(ActionProposal.status == "PENDING_APPROVAL", ActionProposal.expires_at < utcnow())):
        pr.status = "EXPIRED"
    db.flush()


@router.get("")
def list_proposals(status: str | None = None, limit: int = Query(50, ge=1, le=200), db=Depends(get_db), _=Depends(require("read"))):
    _sweep_expired(db)
    db.commit()
    q = select(ActionProposal)
    if status:
        q = q.where(ActionProposal.status == status)
    return {"items": [_out(p) for p in db.scalars(q.order_by(ActionProposal.id.desc()).limit(limit))]}


@router.post("", status_code=201)
def propose(body: ProposalIn, db=Depends(get_db), p=Depends(require("investigate")), settings: Settings = Depends(get_settings)):
    try:
        inc = service.get_or_404(db, body.incident_id)
    except NotFound:
        raise HTTPException(404, "incident not found")
    if inc.execution_mode != "REAL":
        raise HTTPException(409, "Actions require a REAL incident")
    if is_protected(db, body.target, settings):
        raise HTTPException(403, "target is a protected system; destructive actions are denied")
    pr = ActionProposal(incident_id=inc.id, action_type=body.action_type, target=body.target, proposed_by=p.name,
                        status="PENDING_APPROVAL", expires_at=utcnow() + timedelta(minutes=body.ttl_minutes))
    db.add(pr)
    db.commit()
    return _out(pr)


def _decide(db, pid: str, new: str, actor: str, settings: Settings):
    raw = pid.removeprefix("ACT-")
    pr = scoped_get(db, ActionProposal, int(raw)) if raw.isdigit() else None
    if pr is None:
        raise HTTPException(404, "proposal not found")
    if pr.status == "PENDING_APPROVAL" and pr.expires_at < utcnow():
        pr.status = "EXPIRED"
        db.commit()
    incident = service.get_or_404(db, str(pr.incident_id))
    if incident.execution_mode != "REAL":
        raise HTTPException(409, "Actions require a REAL incident")
    if new not in TRANSITIONS.get(pr.status, set()):
        raise HTTPException(409, f"proposal is {pr.status}")
    if pr.proposed_by == actor:
        raise HTTPException(403, "proposer cannot approve/reject their own proposal")
    if new == "APPROVED" and is_protected(db, pr.target, settings):  # re-check at approval time
        raise HTTPException(403, "target is a protected system; destructive actions are denied")
    pr.status, pr.decided_by = new, actor
    db.commit()
    return _out(pr)


@router.post("/{proposal_id}/approve")
def approve(proposal_id: str, db=Depends(get_db), p=Depends(require("approve")), settings: Settings = Depends(get_settings)):
    return _decide(db, proposal_id, "APPROVED", p.name, settings)


@router.post("/{proposal_id}/reject")
def reject(proposal_id: str, db=Depends(get_db), p=Depends(require("approve")), settings: Settings = Depends(get_settings)):
    return _decide(db, proposal_id, "REJECTED", p.name, settings)
