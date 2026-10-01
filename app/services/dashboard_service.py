from __future__ import annotations

import calendar
import datetime as dt
from collections import Counter, defaultdict
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Asset, Department, Maintenance, Technician


class Kpis(TypedDict):
    total_assets: int
    assigned: int
    available: int
    under_repair: int
    pending_repairs: int
    overdue_repairs: int
    maintenance_cost_this_month: float
    active_technicians: int
    total_technicians: int


def get_kpis(session: Session, warranty_alert_days: int = 30) -> Kpis:
    today = dt.date.today()
    month_start = today.replace(day=1)

    total_assets = session.scalar(
        select(func.count()).select_from(Asset).where(Asset.is_active.is_(True))
    ) or 0
    assigned = session.scalar(
        select(func.count()).select_from(Asset).where(Asset.status == "Assigned")
    ) or 0
    available = session.scalar(
        select(func.count()).select_from(Asset).where(Asset.status == "Available")
    ) or 0
    under_repair = session.scalar(
        select(func.count()).select_from(Asset).where(Asset.status == "Under Repair")
    ) or 0

    pending_repairs = session.scalar(
        select(func.count()).select_from(Maintenance)
        .where(Maintenance.is_completed.is_(False))
    ) or 0

    overdue_repairs = session.scalar(
        select(func.count()).select_from(Maintenance).where(
            Maintenance.is_completed.is_(False),
            Maintenance.expected_return_date.is_not(None),
            Maintenance.expected_return_date < today,
        )
    ) or 0

    cost_this_month = session.scalar(
        select(func.coalesce(func.sum(Maintenance.cost), 0.0)).where(
            Maintenance.completed_date.is_not(None),
            Maintenance.completed_date >= month_start,
            Maintenance.completed_date <= today,
        )
    ) or 0.0

    active_technicians = session.scalar(
        select(func.count()).select_from(Technician).where(Technician.is_active.is_(True))
    ) or 0
    total_technicians = session.scalar(select(func.count()).select_from(Technician)) or 0

    return Kpis(
        total_assets=total_assets, assigned=assigned, available=available,
        under_repair=under_repair, pending_repairs=pending_repairs,
        overdue_repairs=overdue_repairs, maintenance_cost_this_month=float(cost_this_month),
        active_technicians=active_technicians, total_technicians=total_technicians,
    )


def get_monthly_cost_trend(session: Session, months: int = 6) -> list[tuple[str, float]]:
    today = dt.date.today()
    rows = session.scalars(
        select(Maintenance).where(
            Maintenance.completed_date.is_not(None),
            Maintenance.cost.is_not(None),
        )
    ).all()

    totals: dict[tuple[int, int], float] = defaultdict(float)
    for m in rows:
        key = (m.completed_date.year, m.completed_date.month)
        totals[key] += m.cost or 0.0

    out = []
    cursor = today.replace(day=1)
    keys = []
    for _ in range(months):
        keys.append((cursor.year, cursor.month))
        cursor = (cursor - dt.timedelta(days=1)).replace(day=1)
    for year, month in reversed(keys):
        label = calendar.month_abbr[month]
        out.append((label, round(totals.get((year, month), 0.0), 2)))
    return out


def get_asset_status_distribution(session: Session) -> list[tuple[str, int]]:
    rows = session.execute(
        select(Asset.status, func.count()).where(Asset.is_active.is_(True)).group_by(Asset.status)
    ).all()
    order = ["Assigned", "Available", "Under Repair", "Retired", "Inactive", "Lost", "Scrapped"]
    counts = dict(rows)
    return [(s, counts[s]) for s in order if s in counts]


def get_repairs_by_department(session: Session, limit: int = 5) -> list[tuple[str, int]]:
    rows = session.execute(
        select(Department.name, func.count(Maintenance.id))
        .join(Maintenance, Maintenance.department_id == Department.id)
        .group_by(Department.name)
        .order_by(func.count(Maintenance.id).desc())
        .limit(limit)
    ).all()
    return [(name, count) for name, count in rows]


def get_warranty_expiring(session: Session, within_days: int = 30) -> list[dict]:
    today = dt.date.today()
    horizon = today + dt.timedelta(days=within_days)
    rows = session.scalars(
        select(Maintenance).where(
            Maintenance.warranty_until.is_not(None),
            Maintenance.warranty_until >= today,
            Maintenance.warranty_until <= horizon,
        ).order_by(Maintenance.warranty_until.asc())
    ).all()

    out = []
    for m in rows:
        asset = m.asset
        out.append({
            "device": m.device_model or (asset.asset_type if asset else "Unknown device"),
            "asset_number": asset.asset_number if asset else "—",
            "department": m.department.name if m.department else "—",
            "days_left": (m.warranty_until - today).days,
        })
    return out


def get_recent_maintenance(session: Session, limit: int = 6) -> list[dict]:
    rows = session.scalars(
        select(Maintenance).order_by(Maintenance.entry_date.desc()).limit(limit)
    ).all()

    today = dt.date.today()
    out = []
    for m in rows:
        display_status = m.status
        if not m.is_completed and m.expected_return_date and m.expected_return_date < today:
            display_status = "Overdue"
        out.append({
            "maintenance_number": m.maintenance_number,
            "device": m.device_model or "—",
            "asset_number": m.asset.asset_number if m.asset else "—",
            "department": m.department.name if m.department else "—",
            "technician": m.technician.name if m.technician else "—",
            "status": display_status,
            "cost": m.cost,
        })
    return out
