from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AssetRepairHistory


def list_repair_history(session: Session, search: str = "") -> list[dict]:
    q = select(AssetRepairHistory).order_by(AssetRepairHistory.repair_date.desc())
    rows = session.scalars(q).all()

    out = []
    for h in rows:
        asset_number = h.asset.asset_number if h.asset else "\u2014"
        if search and search.lower() not in asset_number.lower() \
                and search.lower() not in (h.issue or "").lower():
            continue
        out.append({
            "id": h.id, "asset_number": asset_number,
            "asset_type": h.asset.asset_type if h.asset else "\u2014",
            "repair_date": h.repair_date, "issue": h.issue or "\u2014",
            "repair_details": h.repair_details or "\u2014", "cost": h.cost,
            "technician": h.technician.name if h.technician else "\u2014",
            "status": h.status or "\u2014",
        })
    return out


def summary(rows: list[dict]) -> dict:
    total = len(rows)
    total_cost = sum((r["cost"] or 0) for r in rows)
    return {
        "total_repairs": total,
        "total_cost": total_cost,
        "avg_cost": (total_cost / total) if total else 0,
    }
