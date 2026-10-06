"""Stable JSON representation of persisted incident evidence (no export-time clock)."""
import hashlib
import json
from sqlalchemy import select
from app.incidents import service
from app.incidents.correlation import incident_events
from app.db.repositories.events import EventRepository
from app.db.models import IncidentNote, ActionProposal


def case_pack(db, raw_id):
    inc=service.get_or_404(db,raw_id)
    events=sorted(incident_events(db,inc.id),key=lambda e:(e.event_time,e.event_uid))
    notes=db.scalars(select(IncidentNote).where(IncidentNote.incident_id==inc.id).order_by(IncidentNote.created_at,IncidentNote.id))
    proposals=list(db.scalars(select(ActionProposal).where(ActionProposal.incident_id==inc.id).order_by(ActionProposal.id)))
    pack={"schema_version":"1", "incident_id":inc.code,"tenant_id":inc.tenant_id,"execution_mode":inc.execution_mode,
          "summary":inc.summary or inc.title,"priority":inc.priority,"status":inc.status,"owner":inc.owner,
          "first_seen":inc.opened_at,"last_seen":inc.last_seen,"updated_at":inc.updated_at,
          "affected_assets":sorted({e.host_id for e in events if e.host_id} | ({inc.host_id} if inc.host_id else set())),
          "affected_users":[],"timeline":service.timeline(db,raw_id),
          "evidence_ids":[e.event_uid for e in events],
          "raw_evidence_references":[{"event_uid":e.event_uid,"references":EventRepository(db).refs(e.event_uid,e.execution_mode)} for e in events],
          "correlation":{"reason_codes":sorted(inc.reason_codes),"confidence":inc.confidence,"rule_id":inc.rule_id,"rule_version":inc.rule_version},
          "mitre_mapping":[],"analyst_notes":[{"id":n.id,"actor":n.actor,"created_at":n.created_at,"body":n.body} for n in notes],
          "actions_performed":[],  # No executor exists; approval is not execution.
          "action_proposals":[{"id":p.id,"action_type":p.action_type,"target":p.target,"status":p.status} for p in proposals],
          "ai_analysis_references":[],"final_disposition":inc.disposition}
    from fastapi.encoders import jsonable_encoder
    pack=jsonable_encoder(pack)
    pack["content_sha256"]=hashlib.sha256(json.dumps(pack,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    return pack
