"""Phase 4 — Devices. A device can be deleted only while no Asset still
references it (mirrors the category delete-guard pattern in directory_service).
Phase 8: mutating functions take actor_role (write area "devices")."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Asset, Device
from app.services.directory_service import InUseError
from app.services.permission_service import require_write

DEVICE_STATUSES = ["Available", "Assigned", "Under Repair"]


def _row(d: Device) -> dict:
    return {
        "id": d.id, "model": d.model,
        "category": d.category.name if d.category else "—", "category_id": d.category_id,
        "department": d.department.name if d.department else "—", "department_id": d.department_id,
        "serial_number": d.serial_number or "—", "purchase_date": d.purchase_date,
        "status": d.status,
    }


def list_devices(session: Session, search: str = "", status: str | None = None) -> list[dict]:
    q = select(Device)
    if search:
        like = f"%{search}%"
        q = q.where((Device.model.ilike(like)) | (Device.serial_number.ilike(like)))
    if status:
        q = q.where(Device.status == status)
    devices = session.scalars(q.order_by(Device.model)).all()
    return [_row(d) for d in devices]


def create_device(session: Session, actor_role: str, model: str, category_id, department_id,
                   serial_number: str, purchase_date: dt.date, status: str) -> Device:
    require_write(actor_role, "devices")
    d = Device(
        model=model.strip(), category_id=category_id, department_id=department_id,
        serial_number=serial_number.strip() or None, purchase_date=purchase_date,
        status=status or "Available",
    )
    session.add(d)
    session.commit()
    return d


def update_device(session: Session, actor_role: str, device_id: int, model: str, category_id, department_id,
                   serial_number: str, purchase_date: dt.date, status: str) -> None:
    require_write(actor_role, "devices")
    d = session.get(Device, device_id)
    if d is None:
        raise ValueError("Device not found.")
    d.model = model.strip()
    d.category_id = category_id
    d.department_id = department_id
    d.serial_number = serial_number.strip() or None
    d.purchase_date = purchase_date
    d.status = status or d.status
    session.commit()


def delete_device(session: Session, actor_role: str, device_id: int) -> None:
    require_write(actor_role, "devices")
    in_use = session.scalar(
        select(func.count()).select_from(Asset).where(Asset.device_id == device_id)
    ) or 0
    if in_use:
        raise InUseError(f"{in_use} asset(s) are still linked to this device. Reassign them first.")
    d = session.get(Device, device_id)
    if d is not None:
        session.delete(d)
        session.commit()
