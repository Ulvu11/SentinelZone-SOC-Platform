"""Inventory deltas for investigation context; no maliciousness classification."""
from sqlalchemy import select
from app.db.models import Asset, AssetSnapshot
from app.db.tenancy import scoped_get

FIELDS={"local_users":"new_local_user","services":"new_service","startup_items":"new_startup_item",
        "unsigned_processes":"new_unsigned_process","outbound_destinations":"new_outbound_destination"}


def compare_states(before,after):
    changes=[]
    for field,kind in FIELDS.items():
        for item in sorted(set(after.get(field,[]))-set(before.get(field,[]))):
            changes.append({"kind":kind,"value":item})
    old,new=before.get("telemetry_sources",{}),after.get("telemetry_sources",{})
    for sensor in sorted(old):
        if old[sensor]=="healthy" and new.get(sensor) in ("degraded","offline","stopped"):
            changes.append({"kind":"telemetry_source_stopped","source":sensor,"previous":old[sensor],"current":new[sensor]})
    if before.get("criticality","normal")!=after.get("criticality","normal"):
        changes.append({"kind":"asset_criticality_changed","previous":before.get("criticality","normal"),"current":after.get("criticality","normal")})
    return {"classification":"investigation_context","changes":changes}


def save_snapshot(db,host_id,state,actor):
    if scoped_get(db,Asset,host_id) is None:
        raise LookupError("Asset not found")
    row=AssetSnapshot(host_id=host_id,state=state,actor=actor)
    db.add(row);db.flush()
    return row


def what_changed(db,host_id,before_id=None,after_id=None):
    if scoped_get(db,Asset,host_id) is None:
        raise LookupError("Asset not found")
    if (before_id is None)!=(after_id is None):
        raise ValueError("Supply both before_id and after_id")
    if before_id is None:
        rows=list(db.scalars(select(AssetSnapshot).where(AssetSnapshot.host_id==host_id)
                            .order_by(AssetSnapshot.captured_at.desc(),AssetSnapshot.id.desc()).limit(2)))
        if len(rows)<2:
            return {"classification":"investigation_context","changes":[],"data_complete":False,"reason":"two_snapshots_required"}
        after,before=rows
    else:
        before=scoped_get(db,AssetSnapshot,before_id);after=scoped_get(db,AssetSnapshot,after_id)
        if not before or not after or before.host_id!=host_id or after.host_id!=host_id:
            raise LookupError("Snapshot not found for this asset")
        if (before.captured_at,before.id)>=(after.captured_at,after.id):
            raise ValueError("before must precede after")
    return {**compare_states(before.state,after.state),"before_id":before.id,"after_id":after.id,"data_complete":True}
