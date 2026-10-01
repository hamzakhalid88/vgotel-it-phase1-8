"""
Phase 7 — Reports.

Every report function returns the same shape:
    {"columns": [...], "rows": [[...], ...], "totals": {col: value} | None,
     "summary": [(label, value), ...] | None}
so report_page.py has one generic viewer + one generic exporter instead of
a bespoke screen per report. Column lists double as the export header row.

REPORTS registry at the bottom groups them the way spec section 27 groups
them (Asset / Maintenance / Financial / Warranty) for the Reports hub page.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Asset, AssetRepairHistory, Department, Maintenance, Technician


def _money(v) -> str:
    return f"Rs {v:,.0f}" if v else "Rs 0"


# --------------------------------------------------------------- Asset reports
def asset_register(session: Session, department: str | None = None, status: str | None = None) -> dict:
    q = select(Asset).where(Asset.is_active.is_(True))
    if department:
        q = q.join(Department).where(Department.name == department)
    if status:
        q = q.where(Asset.status == status)
    assets = session.scalars(q.order_by(Asset.asset_number)).all()

    rows = [[
        a.asset_number, a.asset_type, a.serial_number,
        a.department.name if a.department else "\u2014",
        a.client.name if a.client else "\u2014", a.status,
        a.purchase_date.strftime("%d %b %Y") if a.purchase_date else "\u2014",
        a.repair_count,
    ] for a in assets]

    return {
        "columns": ["Asset #", "Type", "Serial number", "Department", "Assigned to", "Status",
                    "Purchase date", "Repairs"],
        "rows": rows, "totals": None,
        "summary": [("Total assets", str(len(assets)))],
    }


def assets_by_department(session: Session) -> dict:
    rows_q = session.execute(
        select(Department.name, func.count(Asset.id))
        .join(Asset, Asset.department_id == Department.id)
        .where(Asset.is_active.is_(True))
        .group_by(Department.name).order_by(func.count(Asset.id).desc())
    ).all()
    total = sum(c for _, c in rows_q)
    return {
        "columns": ["Department", "Assets", "% of total"],
        "rows": [[name, count, f"{count/total*100:.1f}%" if total else "0%"] for name, count in rows_q],
        "totals": {"Assets": total}, "summary": None,
    }


def assets_by_status(session: Session) -> dict:
    rows_q = session.execute(
        select(Asset.status, func.count()).where(Asset.is_active.is_(True)).group_by(Asset.status)
        .order_by(func.count().desc())
    ).all()
    total = sum(c for _, c in rows_q)
    return {
        "columns": ["Status", "Assets", "% of total"],
        "rows": [[s, c, f"{c/total*100:.1f}%" if total else "0%"] for s, c in rows_q],
        "totals": {"Assets": total}, "summary": None,
    }


def assets_by_category(session: Session) -> dict:
    from app.db.models import Category, Device
    rows_q = session.execute(
        select(Category.name, func.count(Asset.id))
        .join(Device, Device.category_id == Category.id)
        .join(Asset, Asset.device_id == Device.id)
        .where(Asset.is_active.is_(True))
        .group_by(Category.name).order_by(func.count(Asset.id).desc())
    ).all()
    total = sum(c for _, c in rows_q)
    return {
        "columns": ["Category", "Assets", "% of total"],
        "rows": [[name, count, f"{count/total*100:.1f}%" if total else "0%"] for name, count in rows_q],
        "totals": {"Assets": total}, "summary": None,
    }


def unassigned_assets(session: Session) -> dict:
    assets = session.scalars(
        select(Asset).where(Asset.is_active.is_(True), Asset.status == "Available")
        .order_by(Asset.asset_number)
    ).all()
    rows = [[a.asset_number, a.asset_type, a.department.name if a.department else "\u2014",
             a.floor or "\u2014", a.purchase_date.strftime("%d %b %Y") if a.purchase_date else "\u2014"]
            for a in assets]
    return {
        "columns": ["Asset #", "Type", "Department", "Floor", "Purchase date"],
        "rows": rows, "totals": None, "summary": [("Unassigned assets", str(len(assets)))],
    }


def repair_frequency(session: Session, threshold: int = 3) -> dict:
    assets = session.scalars(
        select(Asset).where(Asset.is_active.is_(True), Asset.repair_count > 0)
        .order_by(Asset.repair_count.desc())
    ).all()
    rows = [[a.asset_number, a.asset_type, a.department.name if a.department else "\u2014",
             a.repair_count, "High" if a.repair_count >= threshold else "Normal"]
            for a in assets]
    high = sum(1 for a in assets if a.repair_count >= threshold)
    return {
        "columns": ["Asset #", "Type", "Department", "Repair count", "Frequency"],
        "rows": rows, "totals": None,
        "summary": [(f"Assets repaired {threshold}+ times", str(high))],
    }


# ------------------------------------------------------------ Maintenance reports
def maintenance_report(session: Session, date_from: dt.date, date_to: dt.date,
                        status: str | None = None) -> dict:
    q = select(Maintenance).where(
        Maintenance.entry_date >= date_from, Maintenance.entry_date <= date_to
    )
    if status:
        q = q.where(Maintenance.status == status)
    rows_data = session.scalars(q.order_by(Maintenance.entry_date.desc())).all()

    rows = [[
        m.maintenance_number, m.entry_date.strftime("%d %b %Y"),
        m.department.name if m.department else "\u2014", m.device_model or "\u2014",
        m.technician.name if m.technician else "\u2014", m.status,
        _money(m.cost),
    ] for m in rows_data]

    by_status = defaultdict(int)
    for m in rows_data:
        by_status[m.status] += 1
    summary = [(s, str(n)) for s, n in sorted(by_status.items())]

    return {
        "columns": ["Maintenance #", "Entry date", "Department", "Device", "Technician",
                    "Status", "Cost"],
        "rows": rows, "totals": {"Cost": _money(sum(m.cost or 0 for m in rows_data))},
        "summary": summary,
    }


def technician_performance(session: Session) -> dict:
    techs = session.scalars(select(Technician)).all()
    rows = []
    for t in techs:
        total = session.scalar(
            select(func.count()).select_from(Maintenance).where(Maintenance.technician_id == t.id)
        ) or 0
        completed = session.scalar(
            select(func.count()).select_from(Maintenance).where(
                Maintenance.technician_id == t.id, Maintenance.is_completed.is_(True)
            )
        ) or 0
        cost = session.scalar(
            select(func.coalesce(func.sum(Maintenance.cost), 0.0)).where(Maintenance.technician_id == t.id)
        ) or 0.0
        efficiency = f"{completed/total*100:.0f}%" if total else "\u2014"
        rows.append([t.name, t.shop_name or "\u2014", total, completed, efficiency, _money(cost)])
    rows.sort(key=lambda r: r[2], reverse=True)
    return {
        "columns": ["Technician", "Shop", "Total jobs", "Completed", "Efficiency", "Total cost"],
        "rows": rows, "totals": None, "summary": None,
    }


# --------------------------------------------------------------- Financial reports
def department_cost(session: Session, date_from: dt.date, date_to: dt.date) -> dict:
    rows_q = session.execute(
        select(Department.name, func.coalesce(func.sum(Maintenance.cost), 0.0))
        .join(Maintenance, Maintenance.department_id == Department.id)
        .where(Maintenance.completed_date.is_not(None),
               Maintenance.completed_date >= date_from, Maintenance.completed_date <= date_to)
        .group_by(Department.name).order_by(func.sum(Maintenance.cost).desc())
    ).all()
    total = sum(c for _, c in rows_q)
    return {
        "columns": ["Department", "Repair cost"],
        "rows": [[name, _money(cost)] for name, cost in rows_q],
        "totals": {"Repair cost": _money(total)}, "summary": None,
    }


def monthly_repair_cost(session: Session, year: int) -> dict:
    rows_data = session.scalars(
        select(Maintenance).where(Maintenance.completed_date.is_not(None))
    ).all()
    by_month = defaultdict(float)
    for m in rows_data:
        if m.completed_date.year == year:
            by_month[m.completed_date.month] += m.cost or 0
    import calendar
    rows = [[calendar.month_name[mo], _money(by_month.get(mo, 0))] for mo in range(1, 13)]
    return {
        "columns": ["Month", "Repair cost"], "rows": rows,
        "totals": {"Repair cost": _money(sum(by_month.values()))}, "summary": None,
    }


def most_expensive_repairs(session: Session, limit: int = 15) -> dict:
    rows_data = session.scalars(
        select(Maintenance).where(Maintenance.cost.is_not(None))
        .order_by(Maintenance.cost.desc()).limit(limit)
    ).all()
    rows = [[
        m.maintenance_number, m.device_model or "\u2014",
        m.department.name if m.department else "\u2014",
        m.technician.name if m.technician else "\u2014", _money(m.cost),
    ] for m in rows_data]
    return {
        "columns": ["Maintenance #", "Device", "Department", "Technician", "Cost"],
        "rows": rows, "totals": None, "summary": None,
    }


# --------------------------------------------------------------- Warranty reports
def warranty_report(session: Session, which: str) -> dict:
    """which: 'active' | 'expiring' | 'expired'"""
    from app.services.invoice_service import warranty_status
    rows_data = session.scalars(
        select(Maintenance).where(Maintenance.warranty_until.is_not(None))
        .order_by(Maintenance.warranty_until.asc())
    ).all()
    label_map = {"active": "Active", "expiring": "Expiring soon", "expired": "Expired"}
    wanted = label_map[which]
    rows = [[
        m.maintenance_number, m.device_model or "\u2014",
        m.asset.asset_number if m.asset else "\u2014",
        m.warranty_until.strftime("%d %b %Y"), warranty_status(m.warranty_until),
    ] for m in rows_data if warranty_status(m.warranty_until) == wanted]
    return {
        "columns": ["Maintenance #", "Device", "Asset #", "Warranty until", "Status"],
        "rows": rows, "totals": None, "summary": [(f"{wanted} warranties", str(len(rows)))],
    }


REPORTS = {
    "Asset reports": [
        ("asset_register", "Complete asset register", lambda s, f: asset_register(s)),
        ("assets_by_department", "Assets by department", lambda s, f: assets_by_department(s)),
        ("assets_by_status", "Assets by status", lambda s, f: assets_by_status(s)),
        ("assets_by_category", "Assets by category", lambda s, f: assets_by_category(s)),
        ("unassigned_assets", "Unassigned assets", lambda s, f: unassigned_assets(s)),
        ("repair_frequency", "Repair frequency", lambda s, f: repair_frequency(s)),
    ],
    "Maintenance reports": [
        ("maintenance_report", "Maintenance in date range",
         lambda s, f: maintenance_report(s, f["date_from"], f["date_to"])),
        ("technician_performance", "Technician performance", lambda s, f: technician_performance(s)),
    ],
    "Financial reports": [
        ("department_cost", "Repair cost by department",
         lambda s, f: department_cost(s, f["date_from"], f["date_to"])),
        ("monthly_repair_cost", "Monthly repair cost (this year)",
         lambda s, f: monthly_repair_cost(s, dt.date.today().year)),
        ("most_expensive_repairs", "Most expensive repairs", lambda s, f: most_expensive_repairs(s)),
    ],
    "Warranty reports": [
        ("warranty_active", "Active warranties", lambda s, f: warranty_report(s, "active")),
        ("warranty_expiring", "Warranty expiring soon", lambda s, f: warranty_report(s, "expiring")),
        ("warranty_expired", "Expired warranties", lambda s, f: warranty_report(s, "expired")),
    ],
}
