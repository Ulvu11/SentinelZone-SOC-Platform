from sqlalchemy import select

from app.db.models import Incident


class IncidentRepository:
    def __init__(self, session):
        self.s = session

    def page(self, limit: int, cursor: int | None = None, status: str | None = None, priority: str | None = None, execution_mode="REAL"):
        q = select(Incident).where(Incident.execution_mode == execution_mode)
        if status:
            q = q.where(Incident.status == status)
        if priority:
            q = q.where(Incident.priority == priority)
        if cursor:
            q = q.where(Incident.id < cursor)
        rows = list(self.s.scalars(q.order_by(Incident.id.desc()).limit(limit + 1)))
        more = len(rows) > limit
        rows = rows[:limit]
        return rows, (rows[-1].id if more and rows else None)
