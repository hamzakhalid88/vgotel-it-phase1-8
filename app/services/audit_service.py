from __future__ import annotations

import getpass
import socket
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def log_action(
    session: Session,
    user_id: Optional[int],
    action: str,
    entity: str,
    record_id: Optional[int] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
) -> None:
    try:
        computer_name = socket.gethostname()
    except Exception:
        computer_name = getpass.getuser()

    session.add(AuditLog(
        user_id=user_id, action=action, entity=entity, record_id=record_id,
        old_value=old_value, new_value=new_value, computer_name=computer_name,
    ))
    session.commit()
