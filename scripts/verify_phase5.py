"""Run with: python -m scripts.verify_phase5   (from the project root)"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config
from app.db.base import init_engine, session_scope
from app.db.models import Asset, Technician
from app.services import asset_service, maintenance_service as msvc
from sqlalchemy import select

ADMIN = "Administrator"

cfg = load_config()
init_engine(cfg.db_url)

with session_scope() as s:
    print("1. Create a maintenance case for a real seeded asset...")
    asset_row = asset_service.list_assets(s)[0]
    tech_id = s.scalars(select(Technician)).first().id

    m = msvc.create_maintenance(
        s, ADMIN, cfg.maintenance_prefix, cfg.gate_pass_prefix, asset_row["id"],
        "Test issue: does not power on", None, dt.date.today() + dt.timedelta(days=5),
        "Sent for bench repair", "Zeeshan Ahmed", "Created by verify_phase5",
    )
    print(f"   OK — {m.maintenance_number}  gate pass {m.gate_pass_number}  status={m.status}")
    assert m.status == "Received"

    asset_after = s.get(Asset, asset_row["id"])
    assert asset_after.status == "Under Repair"
    print("   OK — asset status flipped to Under Repair")

    print("2. Walk it through the workflow...")
    try:
        msvc.start_repair(s, ADMIN, m.id)
        raise AssertionError("expected WorkflowError: can't start repair before assigning")
    except msvc.WorkflowError as e:
        print(f"   OK — correctly blocked: {e}")

    msvc.assign_technician(s, ADMIN, m.id, tech_id)
    print("   OK — assigned technician, status ->", s.get(type(m), m.id).status)

    msvc.start_repair(s, ADMIN, m.id)
    print("   OK — status ->", s.get(type(m), m.id).status)

    try:
        msvc.complete_repair(s, ADMIN, m.id, "Replaced PSU", -500, dt.date.today(), 6)
        raise AssertionError("expected ValidationError for negative cost")
    except msvc.ValidationError as e:
        print(f"   OK — correctly blocked negative cost: {e}")

    before_count = asset_after.repair_count
    msvc.complete_repair(s, ADMIN, m.id, "Replaced PSU", 4500, dt.date.today(), 6)
    detail = msvc.get_maintenance_detail(s, m.id)
    print(f"   OK — status -> {detail['status']}, warranty_until={detail['warranty_until']}")

    asset_after2 = s.get(Asset, asset_row["id"])
    assert asset_after2.repair_count == before_count + 1
    print(f"   OK — asset repair_count incremented to {asset_after2.repair_count}")

    msvc.return_device(s, ADMIN, m.id, dt.date.today())
    asset_after3 = s.get(Asset, asset_row["id"])
    print(f"   OK — status -> Returned, asset status -> {asset_after3.status}")
    assert asset_after3.status in ("Assigned", "Available")

    try:
        msvc.close_case(s, ADMIN, m.id)
    except msvc.WorkflowError as e:
        raise AssertionError(f"close_case should have succeeded: {e}")
    final = msvc.get_maintenance_detail(s, m.id)
    print(f"   OK — final status = {final['status']}")
    assert final["status"] == "Closed"

    print("3. Repair history reflects the completed repair...")
    detail2 = asset_service.get_asset_detail(s, asset_row["id"])
    assert any(t["details"] == "Replaced PSU" for t in detail2["timeline"])
    print("   OK — new repair appears in the asset's timeline")

    print("4. Phase 8 spot-check: a Viewer cannot advance the workflow...")
    from app.services.permission_service import PermissionError as PermError
    m2 = msvc.create_maintenance(
        s, ADMIN, cfg.maintenance_prefix, cfg.gate_pass_prefix, asset_row["id"],
        "Second test issue", None, dt.date.today() + dt.timedelta(days=5),
        "Sent for bench repair", "Zeeshan Ahmed", "",
    )
    try:
        msvc.assign_technician(s, "Viewer", m2.id, tech_id)
        raise AssertionError("expected PermissionError for Viewer assigning a technician")
    except PermError as e:
        print(f"   OK — correctly blocked: {e}")

print("\nALL PHASE 5 CHECKS PASSED.")
