"""
Phase 5 — Maintenance workflow.

Received -> Assigned -> In Repair -> Completed -> Returned -> Closed.
"Overdue" is never a stored status (spec section 24: it's automatically
derived from expected_return_date, the same way dashboard_service already
computes it) — each function below enforces the one legal forward
transition it represents rather than accepting an arbitrary target status,
so the UI can't push a case into an invalid state.

Completing a repair is the one step with real side effects on Assets
(spec section 24): it writes an AssetRepairHistory row and bumps
Asset.repair_count / last_repair_date. All of it happens inside the
caller's session_scope, so if anything fails, everything rolls back
together (spec section 49).

Phase 8: every mutating function takes actor_role and checks write
access to the "maintenance" area first.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset, AssetRepairHistory, Maintenance
from app.services import numbering_service
from app.services.permission_service import require_write

WORKFLOW_STATUSES = ["Received", "Assigned", "In Repair", "Completed", "Returned", "Closed"]

_AREA = "maintenance"


class WorkflowError(Exception):
    pass


class ValidationError(Exception):
    pass


def _row(m: Maintenance, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    display_status = m.status
    if not m.is_completed and m.status not in ("Returned", "Closed") \
            and m.expected_return_date and m.expected_return_date < today:
        display_status = "Overdue"
    return {
        "id": m.id, "maintenance_number": m.maintenance_number,
        "asset_id": m.asset_id,
        "asset_number": m.asset.asset_number if m.asset else "—",
        "device": m.device_model or "—",
        "department": m.department.name if m.department else "—",
        "employee_name": m.employee_name or "—",
        "issue": m.issue or "—", "repair_details": m.repair_details or "—",
        "cost": m.cost, "status": m.status, "display_status": display_status,
        "technician": m.technician.name if m.technician else "—",
        "technician_id": m.technician_id,
        "technician_shop": m.technician_shop or "—",
        "technician_contact": m.technician_contact or "—",
        "gate_pass_number": m.gate_pass_number or "—",
        "gate_pass_reason": m.gate_pass_reason or "—",
        "authorized_by": m.authorized_by or "—",
        "invoice_number": m.invoice_number or "—",
        "entry_date": m.entry_date, "expected_return_date": m.expected_return_date,
        "actual_return_date": m.actual_return_date, "completed_date": m.completed_date,
        "warranty_months": m.warranty_months, "warranty_until": m.warranty_until,
        "notes": m.notes or "—", "is_completed": m.is_completed,
        "bill_image": m.bill_image,
    }


def list_maintenance(session: Session, search: str = "", status: str | None = None) -> list[dict]:
    q = select(Maintenance)
    if search:
        like = f"%{search}%"
        q = q.where((Maintenance.maintenance_number.ilike(like))
                    | (Maintenance.device_model.ilike(like))
                    | (Maintenance.employee_name.ilike(like)))
    rows = session.scalars(q.order_by(Maintenance.entry_date.desc())).all()
    out = [_row(m) for m in rows]
    if status:
        if status == "Overdue":
            out = [r for r in out if r["display_status"] == "Overdue"]
        else:
            out = [r for r in out if r["status"] == status]
    return out


def get_maintenance_detail(session: Session, maintenance_id: int) -> dict:
    m = session.get(Maintenance, maintenance_id)
    if m is None:
        raise ValueError("Maintenance record not found.")
    return _row(m)


def create_maintenance(session: Session, actor_role: str, mnt_prefix: str, gp_prefix: str, asset_id: int,
                        issue: str, technician_id: int | None, expected_return_date: dt.date,
                        gate_pass_reason: str, authorized_by: str, notes: str) -> Maintenance:
    require_write(actor_role, _AREA)
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise ValueError("Asset not found.")

    technician = None
    if technician_id:
        from app.db.models import Technician
        technician = session.get(Technician, technician_id)

    m = Maintenance(
        maintenance_number=numbering_service.next_maintenance_number(session, mnt_prefix),
        gate_pass_number=numbering_service.next_gate_pass_number(session, gp_prefix),
        asset_id=asset.id, department_id=asset.department_id,
        category_id=asset.device.category_id if asset.device else None,
        technician_id=technician_id,
        employee_name=asset.client.name if asset.client else None,
        device_model=asset.device.model if asset.device else asset.asset_type,
        issue=issue.strip(),
        status="Assigned" if technician_id else "Received",
        gate_pass_reason=gate_pass_reason.strip() or None,
        authorized_by=authorized_by.strip() or None,
        technician_shop=technician.shop_name if technician else None,
        technician_contact=technician.shop_contact if technician else None,
        entry_date=dt.date.today(), expected_return_date=expected_return_date,
        notes=notes.strip() or None, is_completed=False,
    )
    session.add(m)
    asset.status = "Under Repair"
    session.commit()
    return m


def assign_technician(session: Session, actor_role: str, maintenance_id: int, technician_id: int) -> None:
    require_write(actor_role, _AREA)
    from app.db.models import Technician
    m = session.get(Maintenance, maintenance_id)
    if m is None:
        raise ValueError("Maintenance record not found.")
    if m.status not in ("Received", "Assigned"):
        raise WorkflowError(f"Can't assign a technician while status is \u201c{m.status}\u201d.")
    tech = session.get(Technician, technician_id)
    if tech is None:
        raise ValueError("Technician not found.")
    m.technician_id = technician_id
    m.technician_shop = tech.shop_name
    m.technician_contact = tech.shop_contact
    m.status = "Assigned"
    session.commit()


def start_repair(session: Session, actor_role: str, maintenance_id: int) -> None:
    require_write(actor_role, _AREA)
    m = session.get(Maintenance, maintenance_id)
    if m is None:
        raise ValueError("Maintenance record not found.")
    if m.status != "Assigned":
        raise WorkflowError("Assign a technician before starting the repair.")
    m.status = "In Repair"
    session.commit()


def complete_repair(session: Session, actor_role: str, maintenance_id: int, repair_details: str, cost: float,
                     completed_date: dt.date, warranty_months: int) -> None:
    require_write(actor_role, _AREA)
    m = session.get(Maintenance, maintenance_id)
    if m is None:
        raise ValueError("Maintenance record not found.")
    if m.status != "In Repair":
        raise WorkflowError("Only a case that is \u201cIn Repair\u201d can be marked Completed.")
    if completed_date < m.entry_date:
        raise ValidationError("Completed date cannot be before the entry date.")
    if cost is not None and cost < 0:
        raise ValidationError("Cost cannot be negative.")

    m.repair_details = repair_details.strip() or None
    m.cost = cost
    m.completed_date = completed_date
    m.warranty_months = warranty_months or None
    m.warranty_until = (
        completed_date + dt.timedelta(days=30 * warranty_months) if warranty_months else None
    )
    m.status = "Completed"
    m.is_completed = True

    if m.asset_id:
        session.add(AssetRepairHistory(
            asset_id=m.asset_id, repair_date=completed_date, issue=m.issue,
            repair_details=m.repair_details, cost=cost, technician_id=m.technician_id,
            status="Completed",
        ))
        asset = session.get(Asset, m.asset_id)
        if asset:
            asset.repair_count = (asset.repair_count or 0) + 1
            if not asset.last_repair_date or completed_date > asset.last_repair_date:
                asset.last_repair_date = completed_date
    session.commit()


def return_device(session: Session, actor_role: str, maintenance_id: int, actual_return_date: dt.date) -> None:
    require_write(actor_role, _AREA)
    m = session.get(Maintenance, maintenance_id)
    if m is None:
        raise ValueError("Maintenance record not found.")
    if m.status != "Completed":
        raise WorkflowError("Only a Completed case can be marked Returned.")
    m.actual_return_date = actual_return_date
    m.status = "Returned"
    if m.asset_id:
        asset = session.get(Asset, m.asset_id)
        if asset:
            asset.status = "Assigned" if asset.client_id else "Available"
    session.commit()


def close_case(session: Session, actor_role: str, maintenance_id: int) -> None:
    require_write(actor_role, _AREA)
    m = session.get(Maintenance, maintenance_id)
    if m is None:
        raise ValueError("Maintenance record not found.")
    if m.status != "Returned":
        raise WorkflowError("Only a Returned case can be Closed.")
    m.status = "Closed"
    session.commit()


def set_bill_image(session: Session, actor_role: str, maintenance_id: int, relative_path: str) -> None:
    require_write(actor_role, _AREA)
    m = session.get(Maintenance, maintenance_id)
    if m is None:
        raise ValueError("Maintenance record not found.")
    m.bill_image = relative_path
    session.commit()


def clear_bill_image(session: Session, actor_role: str, maintenance_id: int) -> str | None:
    """Clears the DB reference and returns the old relative path so the
    caller can delete the actual file too."""
    require_write(actor_role, _AREA)
    m = session.get(Maintenance, maintenance_id)
    if m is None:
        raise ValueError("Maintenance record not found.")
    old = m.bill_image
    m.bill_image = None
    session.commit()
    return old
