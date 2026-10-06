from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select
from app.auth.permissions import require
from app.db.session import get_db
from app.db.tenancy import scoped_get
from app.db.models import ReplayRun
from app.incidents.case_pack import case_pack
from app.incidents.models import NotFound
from app.incidents import replay
from app.services.what_changed import what_changed,save_snapshot

router=APIRouter(prefix="/v1",tags=["investigations"])


def call(fn,*args):
    try:return fn(*args)
    except (LookupError,NotFound) as exc:raise HTTPException(404,str(exc))
    except ValueError as exc:raise HTTPException(422,str(exc))


@router.get("/incidents/{incident_id}/case-pack")
def export_case_pack(incident_id:str,db=Depends(get_db),_=Depends(require("read"))):
    return call(case_pack,db,incident_id)


class EventSetIn(BaseModel):
    event_uids:list[str]=Field(min_length=1,max_length=10000)
    execution_mode:Literal["REAL","TEST"]="REAL"


@router.post("/event-sets",status_code=201)
def event_set(body:EventSetIn,db=Depends(get_db),p=Depends(require("replay"))):
    row=call(replay.create_event_set,db,body.event_uids,body.execution_mode,p.name)
    db.commit()
    return {"event_set_id":row.id,"tenant_id":row.tenant_id,"content_sha256":row.content_hash,"event_count":len(row.events),"created_at":row.created_at}


class ReplayIn(BaseModel):
    event_set_id:str
    rule_id:str="asset-correlation"
    old_version:str="1"
    new_version:str="2"


def replay_out(row):
    return {"id":row.id,"tenant_id":row.tenant_id,"rule_id":row.rule_id,"old_version":row.old_version,
            "new_version":row.new_version,"event_set_id":row.event_set_id,"old_result":row.old_result,
            "new_result":row.new_result,"run_at":row.run_at,"execution_mode":"REPLAY"}


@router.get("/replay/rules")
def rules(_=Depends(require("read"))):
    return {"rules":replay.RULES}


@router.post("/replay",status_code=201)
def run(body:ReplayIn,db=Depends(get_db),p=Depends(require("replay"))):
    row=call(replay.run_replay,db,body.event_set_id,body.rule_id,body.old_version,body.new_version,p.name)
    db.commit()
    return replay_out(row)


@router.get("/replay/{run_id}")
def get_run(run_id:int,db=Depends(get_db),_=Depends(require("read"))):
    row=scoped_get(db,ReplayRun,run_id)
    if row is None:raise HTTPException(404,"Replay not found")
    return replay_out(row)


class AssetStateIn(BaseModel):
    model_config=ConfigDict(extra="forbid")
    local_users:list[str]=Field(default_factory=list,max_length=10000)
    services:list[str]=Field(default_factory=list,max_length=10000)
    startup_items:list[str]=Field(default_factory=list,max_length=10000)
    unsigned_processes:list[str]=Field(default_factory=list,max_length=10000)
    outbound_destinations:list[str]=Field(default_factory=list,max_length=10000)
    telemetry_sources:dict[str,Literal["healthy","degraded","offline","stopped","unknown"]]=Field(default_factory=dict)
    criticality:Literal["low","normal","high","critical"]="normal"


@router.post("/assets/{host_id}/snapshots",status_code=201)
def snapshot(host_id:str,body:AssetStateIn,db=Depends(get_db),p=Depends(require("admin"))):
    row=call(save_snapshot,db,host_id,body.model_dump(),p.name)
    db.commit()
    return {"snapshot_id":row.id,"host_id":row.host_id,"tenant_id":row.tenant_id,"captured_at":row.captured_at}


@router.get("/assets/{host_id}/what-changed")
def changes(host_id:str,before_id:int | None=None,after_id:int | None=None,db=Depends(get_db),_=Depends(require("read"))):
    return call(what_changed,db,host_id,before_id,after_id)
