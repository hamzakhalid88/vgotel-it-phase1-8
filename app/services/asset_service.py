"""
Phase 4 — Assets.

Business IDs (AST-000001) come from numbering_service, never typed by a
user (spec section 50). Serial numbers must be unique (spec section 36) —
checked explicitly so the person sees "This serial number already exists"
instead of a raw database IntegrityError (spec section 39).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset, AssetRepairHistory
from app.services import numbering_service
from app.services.directory_service import InUseError
from app.services.permission_service import require_write

ASSET_STATUSES = ["Available", "Assigned", "Under Repair", "Inactive", "Lost", "Retired", "Scrapped"]


class DuplicateSerialError(Exception):
    pass


def _row(a: Asset) -> dict:
    return {
        "id": a.id, "asset_number": a.asset_number, "asset_type": a.asset_type,
        "serial_number": a.serial_number,
        "department": a.department.name if a.department else "—",
        "department_id": a.department_id,
        "client": a.client.name if a.client else "—", "client_id": a.client_id,
        "device": a.device.model if a.device else "—", "device_id": a.device_id,
        "floor": a.floor or "—", "status": a.status,
        "purchase_date": a.purchase_date, "vendor": a.vendor or "—",
        "purchase_cost": a.purchase_cost, "repair_count": a.repair_count,
        "last_repair_date": a.last_repair_date, "is_active": a.is_active,
    }


def list_assets(session: Session, search: str = "", status: str | None = None) -> list[dict]:
    q = select(Asset).where(Asset.is_active.is_(True))
    if search:
        like = f"%{search}%"
        q = q.where((Asset.asset_number.ilike(like)) | (Asset.serial_number.ilike(like))
                    | (Asset.asset_type.ilike(like)))
    if status:
        q = q.where(Asset.status == status)
    assets = session.scalars(q.order_by(Asset.asset_number.desc())).all()
    return [_row(a) for a in assets]


def get_asset_detail(session: Session, asset_id: int) -> dict:
    a = session.get(Asset, asset_id)
    if a is None:
        raise ValueError("Asset not found.")

    history = session.scalars(
        select(AssetRepairHistory).where(AssetRepairHistory.asset_id == asset_id)
        .order_by(AssetRepairHistory.repair_date.desc())
    ).all()

    total_cost = sum((h.cost or 0) for h in history)
    timeline = [{
        "date": h.repair_date, "issue": h.issue or "—", "details": h.repair_details or "—",
        "cost": h.cost, "technician": h.technician.name if h.technician else "—",
        "status": h.status or "—",
    } for h in history]

    row = _row(a)
    row.update({
        "repair_total_cost": total_cost,
        "repair_avg_cost": (total_cost / len(history)) if history else 0,
        "timeline": timeline,
    })
    return row


def create_asset(session: Session, actor_role: str, prefix: str, asset_type: str, serial_number: str,
                  department_id, client_id, device_id, floor: str, status: str,
                  purchase_date: dt.date, vendor: str, purchase_cost) -> Asset:
    require_write(actor_role, "assets")
    serial_number = serial_number.strip()
    existing = session.scalar(select(Asset).where(Asset.serial_number == serial_number))
    if existing:
        raise DuplicateSerialError("This serial number already exists. Please enter a unique serial number.")

    asset_number = numbering_service.next_asset_number(session, prefix)
    a = Asset(
        asset_number=asset_number, asset_type=asset_type.strip(), serial_number=serial_number,
        department_id=department_id, client_id=client_id, device_id=device_id,
        floor=floor.strip() or None, status=status or "Available",
        purchase_date=purchase_date, vendor=vendor.strip() or None,
        purchase_cost=purchase_cost, repair_count=0,
    )
    session.add(a)
    session.commit()
    return a


def update_asset(session: Session, actor_role: str, asset_id: int, asset_type: str, serial_number: str,
                  department_id, client_id, device_id, floor: str, status: str,
                  purchase_date: dt.date, vendor: str, purchase_cost) -> None:
    require_write(actor_role, "assets")
    a = session.get(Asset, asset_id)
    if a is None:
        raise ValueError("Asset not found.")

    serial_number = serial_number.strip()
    dupe = session.scalar(
        select(Asset).where(Asset.serial_number == serial_number, Asset.id != asset_id)
    )
    if dupe:
        raise DuplicateSerialError("This serial number already exists. Please enter a unique serial number.")

    a.asset_type = asset_type.strip()
    a.serial_number = serial_number
    a.department_id = department_id
    a.client_id = client_id
    a.device_id = device_id
    a.floor = floor.strip() or None
    a.status = status or a.status
    a.purchase_date = purchase_date
    a.vendor = vendor.strip() or None
    a.purchase_cost = purchase_cost
    a.updated_at = dt.datetime.utcnow()
    session.commit()


def set_asset_active(session: Session, actor_role: str, asset_id: int, active: bool) -> None:
    require_write(actor_role, "assets")
    a = session.get(Asset, asset_id)
    if a is None:
        raise ValueError("Asset not found.")
    if not active and a.status == "Assigned":
        raise InUseError(
            "This asset is still assigned to an employee. Unassign it before deactivating."
        )
    a.is_active = active
    session.commit()
