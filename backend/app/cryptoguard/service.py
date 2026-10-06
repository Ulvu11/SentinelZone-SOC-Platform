import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from fastapi import HTTPException
from sqlalchemy import select
from app.cryptoguard.models import CryptoGuardAgent, CryptoGuardEvent
from app.db.tenancy import scoped_get
from app.ingest import ingest_normalized
from app.normalization.models import NormalizedEvent

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / 'contracts' / 'cryptoguard-telemetry.schema.json').read_text(encoding='utf-8-sig'))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

def validate(payload, agent):
    if not isinstance(payload, dict) or next(VALIDATOR.iter_errors(payload), None):
        raise HTTPException(422, 'invalid CryptoGuard 1.2.0 event')
    if payload['agent_id'] != agent.agent_id:
        raise HTTPException(403, 'agent identity mismatch')
    snapshot = payload.get('snapshot')
    if snapshot and snapshot['host']['platform'].lower() != agent.platform:
        raise HTTPException(422, 'agent platform mismatch')
    for risk in payload['risk']:
        if not isinstance(risk,dict) or risk['security_risk'] != risk['score'] or risk['assessment_source'] != 'heuristic':
            raise HTTPException(422, 'invalid risk provenance')
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def accept(db, agent, payload, settings):
    digest = validate(payload, agent)
    db.scalar(select(CryptoGuardAgent).where(CryptoGuardAgent.agent_id == agent.agent_id).with_for_update())
    existing = scoped_get(db, CryptoGuardEvent, (agent.agent_id, payload['event_uid']))
    if existing:
        if existing.payload_sha256 != digest:
            raise HTTPException(409, 'event UID payload conflict')
        return {'status':'duplicate','durable':True,'agent_id':agent.agent_id,'event_uid':payload['event_uid']}
    if db.scalar(select(CryptoGuardEvent.event_uid).where(CryptoGuardEvent.agent_id==agent.agent_id, CryptoGuardEvent.sequence==payload['sequence'])):
        raise HTTPException(409, 'sequence already used')
    observed = datetime.fromisoformat(payload['observed_at'].replace('Z','+00:00'))
    now = datetime.now(timezone.utc)
    if (observed-now).total_seconds() > 300:
        raise HTTPException(422, 'observation time is in the future')
    db.add(CryptoGuardEvent(agent_id=agent.agent_id, event_uid=payload['event_uid'], sequence=payload['sequence'],
        event_type=payload['event_type'], observed_at=observed, received_at=now, payload_sha256=digest, payload=payload))
    risks = payload['risk']
    security = max((r['security_risk'] for r in risks), default=0) if payload.get('snapshot') else None
    resource = max((r['resource_impact'] for r in risks if r['resource_impact'] is not None), default=None)
    confirmed = [r for r in risks if r['lifecycle']=='confirmed' and r['lifecycle_changed'] and r['severity'] in ('high','critical')]
    score = max((r['security_risk'] for r in confirmed), default=0)
    uid = hashlib.sha256((agent.agent_id+':'+payload['event_uid']).encode()).hexdigest()
    ev=NormalizedEvent(event_uid=uid,event_time=observed,received_at=now,source='cryptoguard',original_sensor='cryptoguard',
        collector_path=['cryptoguard-agent','sentinelzone-ingest'], event_type='behavioral_risk' if confirmed else 'telemetry',
        host_id=agent.host_id,agent_id=agent.agent_id,original_severity=str(security),severity_system='cryptoguard',
        normalized_priority='critical' if any(r['severity']=='critical' for r in confirmed) else 'high' if confirmed else 'low',
        evidence_ref='cryptoguard:'+payload['event_uid'],
        summary=f'CryptoGuard {payload["event_type"]}: security_risk={security}; resource_impact={resource}; assessment_source=agent_heuristic')
    ingest_normalized(db,[ev],settings)
    agent.last_received_at=now
    agent.last_observed_at=max(filter(None,[agent.last_observed_at,observed]))
    db.commit()
    return {'status':'accepted','durable':True,'agent_id':agent.agent_id,'event_uid':payload['event_uid']}

def agent_output(db, agent):
    latest=db.scalar(select(CryptoGuardEvent).where(CryptoGuardEvent.agent_id==agent.agent_id)
        .order_by(CryptoGuardEvent.observed_at.desc(),CryptoGuardEvent.sequence.desc()).limit(1))
    latest_snapshot=db.scalar(select(CryptoGuardEvent).where(CryptoGuardEvent.agent_id==agent.agent_id,
        CryptoGuardEvent.event_type.in_(['telemetry','inventory','risk']))
        .order_by(CryptoGuardEvent.observed_at.desc(),CryptoGuardEvent.sequence.desc()).limit(1))
    payload=latest_snapshot.payload if latest_snapshot else {}
    snapshot=payload.get('snapshot')
    risks=payload.get('risk',[])
    age=(datetime.now(timezone.utc)-agent.last_received_at).total_seconds() if agent.last_received_at else None
    observed_age=(datetime.now(timezone.utc)-agent.last_observed_at).total_seconds() if agent.last_observed_at else None
    return {'agent_id':agent.agent_id,'host_id':agent.host_id,'platform':agent.platform,'enabled':agent.enabled,
        'last_received_at':agent.last_received_at,'last_observed_at':agent.last_observed_at,
        'status':'online' if agent.enabled and age is not None and age<180 and observed_age is not None and observed_age<180 else 'offline',
        'snapshot':snapshot,'health':latest.payload['health'] if latest else None,'risks':risks,
        'security_risk':max((r['security_risk'] for r in risks),default=0) if snapshot else None,
        'resource_impact':max((r['resource_impact'] for r in risks if r['resource_impact'] is not None),default=None),
        'assessment_source':'agent_heuristic','agent_version':payload.get('agent_version')}
