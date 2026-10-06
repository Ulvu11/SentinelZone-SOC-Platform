from datetime import datetime,timezone
from fastapi import Query,HTTPException
from pydantic import AwareDatetime


def time_range(from_time: AwareDatetime | None = Query(None, alias="from"),
               to_time: AwareDatetime | None = Query(None, alias="to")):
    if from_time and to_time and from_time >= to_time:
        raise HTTPException(422, "from must be earlier than to")
    return (from_time.astimezone(timezone.utc) if from_time else None,
            to_time.astimezone(timezone.utc) if to_time else None)


def within(q, column, times):
    start,end=times
    if start:
        q=q.where(column >= start)
    if end:
        q=q.where(column < end)
    return q
