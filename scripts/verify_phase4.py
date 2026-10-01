"""Run with: python -m scripts.verify_phase4   (from the project root)"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config
from app.db.base import init_engine, session_scope
from app.services import asset_service as asvc
from app.services import device_service as dsvc
from app.services.directory_service import InUseError

ADMIN = "Administrator"

cfg = load_config()
init_engine(cfg.db_url)

with session_scope() as s:
    print("1. Assets: list + create + duplicate-serial guard...")
    existing = asvc.list_assets(s)
    print(f"   {len(existing)} active assets, e.g. {existing[0]['asset_number']} ({existing[0]['status']})")

    new_asset = asvc.create_asset(
        s, ADMIN, cfg.asset_prefix, "Laptop", "TEST-SERIAL-0001",
        department_id=None, client_id=None, device_id=None, floor="Test Floor",
        status="Available", purchase_date=dt.date.today(), vendor="Test Vendor", purchase_cost=50000,
    )
    print(f"   OK — created {new_asset.asset_number}")

    try:
        asvc.create_asset(
            s, ADMIN, cfg.asset_prefix, "Laptop", "TEST-SERIAL-0001",
            department_id=None, client_id=None, device_id=None, floor=None,
            status="Available", purchase_date=dt.date.today(), vendor=None, purchase_cost=None,
        )
        raise AssertionError("expected DuplicateSerialError")
    except asvc.DuplicateSerialError as e:
        print(f"   OK — correctly blocked duplicate serial: {e}")

    print("2. Assets: update + detail + guarded deactivate while Assigned...")
    asvc.update_asset(
        s, ADMIN, new_asset.id, "Laptop", "TEST-SERIAL-0001", None, None, None,
        "Test Floor 2", "Assigned", dt.date.today(), "Test Vendor", 55000,
    )
    detail = asvc.get_asset_detail(s, new_asset.id)
    print(f"   OK — detail loaded: status={detail['status']}, repairs={detail['repair_count']}")

    try:
        asvc.set_asset_active(s, ADMIN, new_asset.id, False)
        raise AssertionError("expected InUseError for an Assigned asset")
    except InUseError as e:
        print(f"   OK — correctly blocked: {e}")

    asvc.update_asset(
        s, ADMIN, new_asset.id, "Laptop", "TEST-SERIAL-0001", None, None, None,
        "Test Floor 2", "Available", dt.date.today(), "Test Vendor", 55000,
    )
    asvc.set_asset_active(s, ADMIN, new_asset.id, False)
    print("   OK — deactivated once no longer Assigned")

    print("3. Devices: list + create + update + delete-if-unused guard...")
    devices_before = dsvc.list_devices(s)
    print(f"   {len(devices_before)} devices, e.g. {devices_before[0]['model']}")

    new_device = dsvc.create_device(
        s, ADMIN, "Test Scanner 9000", None, None, "DEV-TEST-0001", dt.date.today(), "Available"
    )
    dsvc.update_device(
        s, ADMIN, new_device.id, "Test Scanner 9000 Pro", None, None,
        "DEV-TEST-0001", dt.date.today(), "Available",
    )
    dsvc.delete_device(s, ADMIN, new_device.id)
    print("   OK — created, updated, deleted an unused device")

    busy_device_id = devices_before[0]["id"]
    try:
        dsvc.delete_device(s, ADMIN, busy_device_id)
        raise AssertionError("expected InUseError for a device with linked assets")
    except InUseError as e:
        print(f"   OK — correctly blocked: {e}")

    print("4. Phase 8 spot-check: an IT Technician can write assets but not devices...")
    from app.services.permission_service import PermissionError as PermError
    ok_asset = asvc.create_asset(
        s, "IT Technician", cfg.asset_prefix, "Laptop", "TEST-SERIAL-0002",
        department_id=None, client_id=None, device_id=None, floor="",
        status="Available", purchase_date=dt.date.today(), vendor="", purchase_cost=None,
    )
    print(f"   OK — IT Technician created {ok_asset.asset_number}")
    try:
        dsvc.create_device(s, "IT Technician", "Should Fail", None, None, "X", dt.date.today(), "Available")
        raise AssertionError("expected PermissionError for IT Technician creating a device")
    except PermError as e:
        print(f"   OK — correctly blocked: {e}")

print("\nALL PHASE 4 CHECKS PASSED.")
