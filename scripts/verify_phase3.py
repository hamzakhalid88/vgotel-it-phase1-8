"""Run with: python -m scripts.verify_phase3   (from the project root)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config
from app.db.base import init_engine, session_scope
from app.services import directory_service as ds

ADMIN = "Administrator"

cfg = load_config()
init_engine(cfg.db_url)

with session_scope() as s:
    print("1. Departments: list + create + update + guarded deactivate...")
    depts_before = ds.list_departments(s)
    print(f"   {len(depts_before)} departments, e.g. {depts_before[0]}")

    new_dept = ds.create_department(s, ADMIN, "Spa & Wellness", "1st Floor", "021-111-0299")
    ds.update_department(s, ADMIN, new_dept.id, "Spa & Wellness", "1st Floor (new wing)", "021-111-0299")
    ds.set_department_active(s, ADMIN, new_dept.id, False)  # no assets yet -> should succeed
    print("   OK — created, updated, deactivated an unused department")

    busy_dept_id = depts_before[0]["id"]
    try:
        ds.set_department_active(s, ADMIN, busy_dept_id, False)
        raise AssertionError("expected InUseError for a department with active assets")
    except ds.InUseError as e:
        print(f"   OK — correctly blocked: {e}")

    print("2. Categories: create + delete-if-unused guard...")
    new_cat = ds.create_category(s, ADMIN, "Scanner", "Barcode / document scanners")
    ds.delete_category(s, ADMIN, new_cat.id)  # unused -> should succeed
    print("   OK — created and deleted an unused category")

    busy_cat_id = ds.list_categories(s)[0]["id"]
    try:
        ds.delete_category(s, ADMIN, busy_cat_id)
        raise AssertionError("expected InUseError for a category with devices")
    except ds.InUseError as e:
        print(f"   OK — correctly blocked: {e}")

    print("3. Clients: create + update + deactivate...")
    c = ds.create_client(s, ADMIN, "Test Person", depts_before[0]["id"], "0300-0000000",
                          "test@vgotel.pk", "Officer")
    ds.update_client(s, ADMIN, c.id, "Test Person Jr", depts_before[0]["id"], "0300-0000000",
                      "test@vgotel.pk", "Officer")
    ds.set_client_active(s, ADMIN, c.id, False)
    print("   OK — created, updated, deactivated a client")

    print("4. Technicians: create + update + guarded deactivate...")
    t = ds.create_technician(s, ADMIN, "Test Tech", "0300-1111111", "tt@example.com",
                              "Karachi", "Test Shop", "021-000-0000")
    ds.update_technician(s, ADMIN, t.id, "Test Tech II", "0300-1111111", "tt@example.com",
                          "Karachi", "Test Shop", "021-000-0000")
    ds.set_technician_active(s, ADMIN, t.id, False)  # no jobs yet -> should succeed
    print("   OK — created, updated, deactivated a technician with no open jobs")

    busy_tech_id = ds.list_technicians(s)[0]["id"]
    # (may or may not have open jobs depending on seed randomness — report either way)
    try:
        ds.set_technician_active(s, ADMIN, busy_tech_id, False)
        print("   (this technician had no open jobs, deactivation allowed)")
        ds.set_technician_active(s, ADMIN, busy_tech_id, True)  # restore
    except ds.InUseError as e:
        print(f"   OK — correctly blocked: {e}")

    print("5. Phase 8 spot-check: a Viewer cannot write to directory...")
    from app.services.permission_service import PermissionError as PermError
    try:
        ds.create_department(s, "Viewer", "Should Fail", "Nowhere", "000")
        raise AssertionError("expected PermissionError for Viewer creating a department")
    except PermError as e:
        print(f"   OK — correctly blocked: {e}")

print("\nALL PHASE 3 CHECKS PASSED.")
