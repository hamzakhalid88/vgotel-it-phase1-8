"""
Phase 6 — Invoices and warranty status.

An invoice is generated FROM a completed maintenance case, not created
standalone (spec section 22's field list — Technician, Shop, Department,
Device, Repair Cost, Warranty — are all already on the Maintenance record
once it's Completed). generate_invoice() is the one write in this module;
everything else is read/derive.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Maintenance
from app.services import numbering_service
from app.services.permission_service import require_write


class InvoiceError(Exception):
    pass


def warranty_status(warranty_until: dt.date | None, today: dt.date | None = None) -> str:
    if not warranty_until:
        return "\u2014"
    today = today or dt.date.today()
    if warranty_until < today:
        return "Expired"
    if (warranty_until - today).days <= 30:
        return "Expiring soon"
    return "Active"


def _row(m: Maintenance) -> dict:
    return {
        "id": m.id, "maintenance_number": m.maintenance_number,
        "invoice_number": m.invoice_number,
        "date": m.completed_date or m.entry_date,
        "department": m.department.name if m.department else "\u2014",
        "device": m.device_model or "\u2014",
        "asset_number": m.asset.asset_number if m.asset else "\u2014",
        "technician": m.technician.name if m.technician else "\u2014",
        "technician_shop": m.technician_shop or "\u2014",
        "cost": m.cost, "notes": m.notes or "\u2014",
        "warranty_months": m.warranty_months, "warranty_until": m.warranty_until,
        "warranty_status": warranty_status(m.warranty_until),
        "status": m.status,
    }


def list_invoices(session: Session, search: str = "") -> list[dict]:
    q = select(Maintenance).where(Maintenance.invoice_number.is_not(None))
    if search:
        like = f"%{search}%"
        q = q.where((Maintenance.invoice_number.ilike(like))
                    | (Maintenance.device_model.ilike(like)))
    rows = session.scalars(q.order_by(Maintenance.completed_date.desc())).all()
    return [_row(m) for m in rows]


def list_uninvoiced_completed(session: Session) -> list[dict]:
    """Completed-or-later cases that don't have an invoice yet — the
    candidates 'Generate invoice' can act on."""
    q = select(Maintenance).where(
        Maintenance.status.in_(("Completed", "Returned", "Closed")),
        Maintenance.invoice_number.is_(None),
    ).order_by(Maintenance.completed_date.desc())
    return [_row(m) for m in session.scalars(q).all()]


def get_invoice_detail(session: Session, maintenance_id: int) -> dict:
    m = session.get(Maintenance, maintenance_id)
    if m is None:
        raise ValueError("Maintenance record not found.")
    if not m.invoice_number:
        raise InvoiceError("No invoice has been generated for this case yet.")
    return _row(m)


def generate_invoice(session: Session, actor_role: str, maintenance_id: int, prefix: str) -> str:
    require_write(actor_role, "invoices")
    m = session.get(Maintenance, maintenance_id)
    if m is None:
        raise ValueError("Maintenance record not found.")
    if m.status not in ("Completed", "Returned", "Closed"):
        raise InvoiceError("An invoice can only be generated once the repair is Completed.")
    if m.cost is None:
        raise InvoiceError("This case has no cost recorded yet.")
    if m.invoice_number:
        return m.invoice_number  # already generated — idempotent, not an error
    m.invoice_number = numbering_service.next_invoice_number(session, prefix)
    session.commit()
    return m.invoice_number
