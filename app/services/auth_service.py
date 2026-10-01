from __future__ import annotations

import datetime as dt
from typing import Optional

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Hash was not a valid bcrypt hash (e.g. legacy plain-text row
        # mid-migration) — never treat that as a silent match.
        return False


def authenticate(session: Session, username: str, password: str) -> Optional[User]:
    user = session.scalar(
        select(User).where(User.username == username, User.is_active.is_(True))
    )
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    user.last_login_at = dt.datetime.utcnow()
    session.commit()
    return user
