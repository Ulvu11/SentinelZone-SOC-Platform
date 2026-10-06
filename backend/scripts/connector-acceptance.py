"""Read-only upstream contract probe. Prints counts/status only; never credentials/raw records.
Run after configuring .env: python scripts/connector-acceptance.py --fetch --minutes 15
This does not write to the backend database or dispatch any notifications.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import get_settings
from app.connectors.cryptoguard import build_connectors
from app.normalization.normalizer import normalize

async def run(args):
    settings=get_settings().validate_runtime()
    result=[]
    until=datetime.now(timezone.utc);since=until-timedelta(minutes=args.minutes)
    for connector in build_connectors(settings):
        row={"connector":connector.name,"mode":connector.mode,"live_tested":False}
        if connector.mode!="live":
            row["status"]="not_configured";result.append(row);continue
        try:
            health=await connector.health()
            row.update(status=health.status,live_tested=True)
            if health.error:row["error"]=health.error
            if args.fetch and health.status=="healthy":
                raws=await connector.fetch_events(since,until)
                sensors=Counter();bad=0;times=[]
                for raw in raws:
                    try:
                        ev=normalize(raw.kind,raw.payload,raw.collector_path)
                        sensors[ev.original_sensor]+=1;times.append(ev.event_time)
                    except (KeyError,ValueError,TypeError):bad+=1
                row.update(received=len(raws),normalized_sensors=dict(sensors),rejected=bad,
                           latest_event_at=max(times).isoformat() if times else None)
                if bad:row["status"]="degraded"
        except Exception as exc:
            row.update(status="unavailable",error_type=type(exc).__name__)
        result.append(row)
    print(json.dumps({"scope":"read-only contract probe; zero notifications/actions", "connectors":result},indent=2))
    return 0 if all(r["status"]=="healthy" for r in result) else 1

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch",action="store_true")
    parser.add_argument("--minutes",type=int,default=15,choices=range(1,1441),metavar="1..1440")
    sys.exit(asyncio.run(run(parser.parse_args())))
