import json
import secrets
from datetime import datetime,timedelta,timezone
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Header,HTTPException,Query,Request,Response
from pydantic import BaseModel,Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.auth.permissions import require
from app.auth.users import hash_token
from app.config import get_settings
from app.cryptoguard.models import CryptoGuardAgent,CryptoGuardEnrollment,CryptoGuardEvent
from app.cryptoguard.service import accept,agent_output
from app.db.models import AuditLog
from app.db.session import get_db
from app.db.tenancy import bind_tenant,scoped_get

router=APIRouter(prefix='/v1/cryptoguard',tags=['cryptoguard'])

def bearer(authorization):
    if not authorization or not authorization.lower().startswith('bearer '): raise HTTPException(401,'missing bearer token')
    return authorization[7:].strip()

def agent_principal(authorization:str|None=Header(default=None),db=Depends(get_db)):
    digest=hash_token(bearer(authorization))
    table=CryptoGuardAgent.__table__
    row=db.connection().execute(select(table.c.tenant_id,table.c.agent_id).where(table.c.token_hash==digest,table.c.enabled.is_(True))).first()
    if not row: raise HTTPException(401,'invalid agent credential')
    bind_tenant(db,row.tenant_id)
    return scoped_get(db,CryptoGuardAgent,row.agent_id)

class EnrollmentRequest(BaseModel):
    agent_id:UUID
    platform:Literal['windows','linux']
    expires_minutes:int=Field(default=30,ge=1,le=120)

@router.post('/enrollment-tokens',status_code=201)
def ticket(body:EnrollmentRequest,response:Response,db=Depends(get_db),p=Depends(require('admin'))):
    token=secrets.token_urlsafe(32)
    db.add(CryptoGuardEnrollment(token_hash=hash_token(token),agent_id=str(body.agent_id),platform=body.platform,
        expires_at=datetime.now(timezone.utc)+timedelta(minutes=body.expires_minutes)))
    db.add(AuditLog(actor=p.name,action='CRYPTOGUARD_ENROLLMENT_ISSUED',detail={'agent_id':str(body.agent_id),'platform':body.platform}))
    db.commit();response.headers['Cache-Control']='no-store'
    return {'enrollment_token':token,'expires_in_seconds':body.expires_minutes*60}

class EnrollBody(BaseModel):
    agent_id:UUID
    platform:Literal['windows','linux']

@router.post('/enroll',status_code=201)
def enroll(body:EnrollBody,response:Response,authorization:str|None=Header(default=None),db=Depends(get_db)):
    digest=hash_token(bearer(authorization));table=CryptoGuardEnrollment.__table__
    row=db.connection().execute(select(table.c.tenant_id).where(table.c.token_hash==digest)).first()
    if not row: raise HTTPException(401,'invalid enrollment credential')
    bind_tenant(db,row.tenant_id)
    item=db.scalar(select(CryptoGuardEnrollment).where(CryptoGuardEnrollment.token_hash==digest).with_for_update())
    now=datetime.now(timezone.utc)
    if not item or item.used_at or item.expires_at<=now: raise HTTPException(401,'expired or used enrollment credential')
    if item.agent_id!=str(body.agent_id) or item.platform!=body.platform: raise HTTPException(403,'enrollment identity mismatch')
    agent=scoped_get(db,CryptoGuardAgent,str(body.agent_id))
    if agent: raise HTTPException(409,'agent already enrolled; rotate its credential explicitly')
    token=secrets.token_urlsafe(32)
    db.add(CryptoGuardAgent(agent_id=str(body.agent_id),host_id='cg-'+str(body.agent_id),platform=body.platform,token_hash=hash_token(token)))
    item.used_at=now;db.commit();response.headers['Cache-Control']='no-store'
    return {'agent_id':str(body.agent_id),'agent_token':token,'telemetry_path':'/v1/cryptoguard/telemetry'}

@router.post('/telemetry')
async def telemetry(request:Request,response:Response,agent=Depends(agent_principal),db=Depends(get_db),settings=Depends(get_settings)):
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>16*1024*1024: raise HTTPException(413,'event too large')
    try: payload=json.loads(raw,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError,UnicodeError,RecursionError): raise HTTPException(422,'invalid JSON event') from None
    try: result=accept(db,agent,payload,settings)
    except IntegrityError:
        db.rollback();raise HTTPException(409,'event identity conflict; retry unchanged event') from None
    response.headers['Cache-Control']='no-store'
    return result

@router.get('/agents')
def agents(limit:int=Query(100,ge=1,le=500),cursor:str|None=None,db=Depends(get_db),_=Depends(require('read'))):
    q=select(CryptoGuardAgent).order_by(CryptoGuardAgent.agent_id)
    if cursor:q=q.where(CryptoGuardAgent.agent_id>cursor)
    rows=list(db.scalars(q.limit(limit+1)))
    return {'items':[agent_output(db,a) for a in rows[:limit]],'next_cursor':rows[limit-1].agent_id if len(rows)>limit else None}

@router.get('/agents/{agent_id}')
def agent(agent_id:UUID,db=Depends(get_db),_=Depends(require('read'))):
    a=scoped_get(db,CryptoGuardAgent,str(agent_id))
    if not a:raise HTTPException(404,'agent not found')
    return agent_output(db,a)

@router.post('/agents/{agent_id}/revoke',status_code=204)
def revoke(agent_id:UUID,db=Depends(get_db),p=Depends(require('admin'))):
    a=scoped_get(db,CryptoGuardAgent,str(agent_id))
    if not a:raise HTTPException(404,'agent not found')
    a.enabled=False;db.add(AuditLog(actor=p.name,action='CRYPTOGUARD_AGENT_REVOKED',detail={'agent_id':str(agent_id)}));db.commit()

@router.get('/risks')
def risks(limit:int=Query(100,ge=1,le=500),db=Depends(get_db),_=Depends(require('read'))):
    rows=list(db.scalars(select(CryptoGuardEvent).where(CryptoGuardEvent.event_type=='risk').order_by(CryptoGuardEvent.observed_at.desc()).limit(limit)))
    return {'items':[{'agent_id':r.agent_id,'event_uid':r.event_uid,'observed_at':r.observed_at,'risks':r.payload['risk']} for r in rows]}
