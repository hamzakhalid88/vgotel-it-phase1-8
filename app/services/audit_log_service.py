from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, User

ACTIONS = ["Create", "Update", "Delete", "StatusChange", "Login", "LoginFailed"]


def list_audit_log(
    session: Session, search: str = "", entity: str | None = None, action: str | None = None,
    date_from: dt.date | None = None, date_to: dt.date | None = None, limit: int = 300,
) -> list[dict]:
    q = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    if entity:
        q = q.where(AuditLog.entity == entity)
    if action:
        q = q.where(AuditLog.action == action)
    if date_from:
        q = q.where(AuditLog.timestamp >= dt.datetime.combine(date_from, dt.time.min))
    if date_to:
        q = q.where(AuditLog.timestamp <= dt.datetime.combine(date_to, dt.time.max))

    logs = session.scalars(q).all()
    out = []
    for log in logs:
        user = session.get(User, log.user_id) if log.user_id else None
        user_name = user.full_name if user else "\u2014"
        if search:
            haystack = f"{user_name} {log.action} {log.entity} {log.old_value or ''} {log.new_value or ''}".lower()
            if search.lower() not in haystack:
                continue
        out.append({
            "id": log.id, "timestamp": log.timestamp, "user": user_name,
            "action": log.action, "entity": log.entity, "record_id": log.record_id,
            "old_value": log.old_value or "\u2014", "new_value": log.new_value or "\u2014",
            "computer_name": log.computer_name or "\u2014",
        })
    return out


def distinct_entities(session: Session) -> list[str]:
    rows = session.execute(select(AuditLog.entity).distinct().order_by(AuditLog.entity)).all()
    return [r[0] for r in rows]
