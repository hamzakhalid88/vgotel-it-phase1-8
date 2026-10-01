"""
Phase 3 business logic: Departments, Categories, Clients, Technicians.

All four are simple master-data entities, so they share one pattern here:
list_x() returns dicts (not raw ORM rows) with the usage counts the brief
asks each list screen to show (section 13/14/15/20), create_x()/update_x()
write through session_scope callers pass in, and deactivate_x() is a soft
delete (spec section 38) that is blocked if the record is still
referenced elsewhere (spec section 15's "prevent deleting a category
still in use" rule, applied consistently to all four).

Phase 8: every mutating function takes actor_role and checks it first
(spec section 31 — "enforce permissions at service/business layer, not
only UI"). All four entities share the "directory" write area.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Asset, Category, Client, Department, Device, Maintenance, Technician,
)
from app.services.permission_service import require_write

_AREA = "directory"


class InUseError(Exception):
    """Raised when a deactivate would orphan records that reference it."""


# ---------------------------------------------------------------- Departments
def list_departments(session: Session, search: str = "") -> list[dict]:
    q = select(Department)
    if search:
        q = q.where(Department.name.ilike(f"%{search}%"))
    depts = session.scalars(q.order_by(Department.name)).all()

    out = []
    for d in depts:
        asset_count = session.scalar(
            select(func.count()).select_from(Asset).where(Asset.department_id == d.id)
        ) or 0
        device_count = session.scalar(
            select(func.count()).select_from(Device).where(Device.department_id == d.id)
        ) or 0
        client_count = session.scalar(
            select(func.count()).select_from(Client).where(Client.department_id == d.id)
        ) or 0
        maint_count = session.scalar(
            select(func.count()).select_from(Maintenance).where(Maintenance.department_id == d.id)
        ) or 0
        out.append({
            "id": d.id, "name": d.name, "location": d.location or "—", "phone": d.phone or "—",
            "is_active": d.is_active, "assets": asset_count, "devices": device_count,
            "clients": client_count, "maintenance": maint_count,
        })
    return out


def create_department(session: Session, actor_role: str, name: str, location: str, phone: str) -> Department:
    require_write(actor_role, _AREA)
    d = Department(name=name.strip(), location=location.strip() or None, phone=phone.strip() or None)
    session.add(d)
    session.commit()
    return d


def update_department(session: Session, actor_role: str, dept_id: int, name: str, location: str, phone: str) -> None:
    require_write(actor_role, _AREA)
    d = session.get(Department, dept_id)
    if d is None:
        raise ValueError("Department not found.")
    d.name, d.location, d.phone = name.strip(), location.strip() or None, phone.strip() or None
    session.commit()


def set_department_active(session: Session, actor_role: str, dept_id: int, active: bool) -> None:
    require_write(actor_role, _AREA)
    d = session.get(Department, dept_id)
    if d is None:
        raise ValueError("Department not found.")
    if not active:
        in_use = session.scalar(
            select(func.count()).select_from(Asset).where(
                Asset.department_id == dept_id, Asset.is_active.is_(True)
            )
        ) or 0
        if in_use:
            raise InUseError(f"{in_use} active asset(s) are still assigned to this department.")
    d.is_active = active
    session.commit()


# ------------------------------------------------------------------ Categories
def list_categories(session: Session, search: str = "") -> list[dict]:
    q = select(Category)
    if search:
        q = q.where(Category.name.ilike(f"%{search}%"))
    cats = session.scalars(q.order_by(Category.name)).all()

    out = []
    for c in cats:
        device_count = session.scalar(
            select(func.count()).select_from(Device).where(Device.category_id == c.id)
        ) or 0
        maint_count = session.scalar(
            select(func.count()).select_from(Maintenance).where(Maintenance.category_id == c.id)
        ) or 0
        out.append({
            "id": c.id, "name": c.name, "description": c.description or "—",
            "devices": device_count, "maintenance": maint_count,
        })
    return out


def create_category(session: Session, actor_role: str, name: str, description: str) -> Category:
    require_write(actor_role, _AREA)
    c = Category(name=name.strip(), description=description.strip() or None)
    session.add(c)
    session.commit()
    return c


def update_category(session: Session, actor_role: str, cat_id: int, name: str, description: str) -> None:
    require_write(actor_role, _AREA)
    c = session.get(Category, cat_id)
    if c is None:
        raise ValueError("Category not found.")
    c.name, c.description = name.strip(), description.strip() or None
    session.commit()


def delete_category(session: Session, actor_role: str, cat_id: int) -> None:
    """Spec section 15: block deletion while the category is still in use."""
    require_write(actor_role, _AREA)
    device_count = session.scalar(
        select(func.count()).select_from(Device).where(Device.category_id == cat_id)
    ) or 0
    if device_count:
        raise InUseError(
            f"{device_count} device(s) still use this category. Reassign them first."
        )
    c = session.get(Category, cat_id)
    if c is not None:
        session.delete(c)
        session.commit()


# ---------------------------------------------------------------------- Clients
def list_clients(session: Session, search: str = "") -> list[dict]:
    q = select(Client)
    if search:
        q = q.where(Client.name.ilike(f"%{search}%"))
    clients = session.scalars(q.order_by(Client.name)).all()

    out = []
    for c in clients:
        asset_count = session.scalar(
            select(func.count()).select_from(Asset).where(
                Asset.client_id == c.id, Asset.is_active.is_(True)
            )
        ) or 0
        out.append({
            "id": c.id, "name": c.name,
            "department": c.department.name if c.department else "—",
            "department_id": c.department_id,
            "phone": c.phone or "—", "email": c.email or "—",
            "designation": c.designation or "—", "is_active": c.is_active,
            "assigned_assets": asset_count,
        })
    return out


def create_client(session: Session, actor_role: str, name: str, department_id: int | None, phone: str,
                   email: str, designation: str) -> Client:
    require_write(actor_role, _AREA)
    c = Client(name=name.strip(), department_id=department_id, phone=phone.strip() or None,
               email=email.strip() or None, designation=designation.strip() or None)
    session.add(c)
    session.commit()
    return c


def update_client(session: Session, actor_role: str, client_id: int, name: str, department_id: int | None,
                   phone: str, email: str, designation: str) -> None:
    require_write(actor_role, _AREA)
    c = session.get(Client, client_id)
    if c is None:
        raise ValueError("Client not found.")
    c.name = name.strip()
    c.department_id = department_id
    c.phone = phone.strip() or None
    c.email = email.strip() or None
    c.designation = designation.strip() or None
    session.commit()


def set_client_active(session: Session, actor_role: str, client_id: int, active: bool) -> None:
    require_write(actor_role, _AREA)
    c = session.get(Client, client_id)
    if c is None:
        raise ValueError("Client not found.")
    c.is_active = active
    session.commit()


# ----------------------------------------------------------------- Technicians
def list_technicians(session: Session, search: str = "") -> list[dict]:
    q = select(Technician)
    if search:
        q = q.where(Technician.name.ilike(f"%{search}%"))
    techs = session.scalars(q.order_by(Technician.name)).all()

    out = []
    for t in techs:
        total_jobs = session.scalar(
            select(func.count()).select_from(Maintenance).where(Maintenance.technician_id == t.id)
        ) or 0
        completed_jobs = session.scalar(
            select(func.count()).select_from(Maintenance).where(
                Maintenance.technician_id == t.id, Maintenance.is_completed.is_(True)
            )
        ) or 0
        total_cost = session.scalar(
            select(func.coalesce(func.sum(Maintenance.cost), 0.0)).where(
                Maintenance.technician_id == t.id
            )
        ) or 0.0
        out.append({
            "id": t.id, "name": t.name, "phone": t.phone or "—", "email": t.email or "—",
            "shop_name": t.shop_name or "—", "shop_contact": t.shop_contact or "—",
            "is_active": t.is_active, "total_jobs": total_jobs,
            "completed_jobs": completed_jobs, "total_cost": total_cost,
        })
    return out


def create_technician(session: Session, actor_role: str, name: str, phone: str, email: str, address: str,
                       shop_name: str, shop_contact: str) -> Technician:
    require_write(actor_role, _AREA)
    t = Technician(name=name.strip(), phone=phone.strip() or None, email=email.strip() or None,
                    address=address.strip() or None, shop_name=shop_name.strip() or None,
                    shop_contact=shop_contact.strip() or None)
    session.add(t)
    session.commit()
    return t


def update_technician(session: Session, actor_role: str, tech_id: int, name: str, phone: str, email: str,
                       address: str, shop_name: str, shop_contact: str) -> None:
    require_write(actor_role, _AREA)
    t = session.get(Technician, tech_id)
    if t is None:
        raise ValueError("Technician not found.")
    t.name = name.strip()
    t.phone = phone.strip() or None
    t.email = email.strip() or None
    t.address = address.strip() or None
    t.shop_name = shop_name.strip() or None
    t.shop_contact = shop_contact.strip() or None
    session.commit()


def set_technician_active(session: Session, actor_role: str, tech_id: int, active: bool) -> None:
    require_write(actor_role, _AREA)
    t = session.get(Technician, tech_id)
    if t is None:
        raise ValueError("Technician not found.")
    if not active:
        open_jobs = session.scalar(
            select(func.count()).select_from(Maintenance).where(
                Maintenance.technician_id == tech_id, Maintenance.is_completed.is_(False)
            )
        ) or 0
        if open_jobs:
            raise InUseError(f"{open_jobs} open job(s) are still assigned to this technician.")
    t.is_active = active
    session.commit()
