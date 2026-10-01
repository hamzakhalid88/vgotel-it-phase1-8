"""
Phase 8 — User management.

Manage Users is its own permission the brief calls out separately from
the four roles' general write access (section 31), so this module checks
permission_service.can_manage_users() directly rather than going through
require_write()/WRITE_AREAS — only Administrator ever passes.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.services.auth_service import hash_password
from app.services.permission_service import ROLES, PermissionError, can_manage_users


class UserServiceError(Exception):
    pass


def _require_admin(actor_role: str) -> None:
    if not can_manage_users(actor_role):
        raise PermissionError(f"{actor_role} cannot manage users.")


def _row(u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "full_name": u.full_name,
        "role": u.role, "is_active": u.is_active,
        "last_login_at": u.last_login_at,
    }


def list_users(session: Session, search: str = "") -> list[dict]:
    q = select(User)
    if search:
        like = f"%{search}%"
        q = q.where((User.username.ilike(like)) | (User.full_name.ilike(like)))
    users = session.scalars(q.order_by(User.username)).all()
    return [_row(u) for u in users]


def create_user(session: Session, actor_role: str, username: str, full_name: str,
                 role: str, password: str) -> User:
    _require_admin(actor_role)
    if role not in ROLES:
        raise ValueError(f"Unknown role: {role!r}")
    username = username.strip().lower()
    if not username or not password:
        raise UserServiceError("Username and password are both required.")
    existing = session.scalar(select(User).where(User.username == username))
    if existing:
        raise UserServiceError(f"Username \u201c{username}\u201d is already taken.")

    u = User(username=username, password_hash=hash_password(password),
              full_name=full_name.strip(), role=role, is_active=True)
    session.add(u)
    session.commit()
    return u


def update_user(session: Session, actor_role: str, user_id: int, full_name: str, role: str) -> None:
    _require_admin(actor_role)
    if role not in ROLES:
        raise ValueError(f"Unknown role: {role!r}")
    u = session.get(User, user_id)
    if u is None:
        raise ValueError("User not found.")
    if u.role == "Administrator" and role != "Administrator":
        _guard_last_admin(session, exclude_user_id=user_id)
    u.full_name = full_name.strip()
    u.role = role
    session.commit()


def set_user_active(session: Session, actor_role: str, user_id: int, active: bool) -> None:
    _require_admin(actor_role)
    u = session.get(User, user_id)
    if u is None:
        raise ValueError("User not found.")
    if not active and u.role == "Administrator":
        _guard_last_admin(session, exclude_user_id=user_id)
    u.is_active = active
    session.commit()


def reset_password(session: Session, actor_role: str, user_id: int, new_password: str) -> None:
    _require_admin(actor_role)
    if not new_password:
        raise UserServiceError("New password can't be empty.")
    u = session.get(User, user_id)
    if u is None:
        raise ValueError("User not found.")
    u.password_hash = hash_password(new_password)
    session.commit()


def _guard_last_admin(session: Session, exclude_user_id: int) -> None:
    """Refuse to demote/deactivate the only remaining active Administrator
    — otherwise nobody could manage users again without touching the DB
    directly."""
    other_admins = session.scalar(
        select(User).where(
            User.role == "Administrator", User.is_active.is_(True), User.id != exclude_user_id
        )
    )
    if other_admins is None:
        raise UserServiceError(
            "This is the last active Administrator account — promote another "
            "user to Administrator first."
        )
