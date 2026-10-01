"""Run with: python -m scripts.verify_phase8   (from the project root)"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config
from app.db.base import init_engine, session_scope
from app.services import (
    asset_service, audit_log_service, audit_service, device_service,
    directory_service as ds, maintenance_service as msvc, user_service,
)
from app.services import permission_service as perm
from app.services import invoice_service as isvc

cfg = load_config()
init_engine(cfg.db_url)

print("1. Page access matrix...")
assert perm.can_view_page("Administrator", "users_roles")
assert perm.can_view_page("Administrator", "settings")
assert not perm.can_view_page("IT Manager", "users_roles")
assert not perm.can_view_page("IT Manager", "settings")
assert perm.can_view_page("IT Manager", "reports")
assert not perm.can_view_page("IT Technician", "reports")
assert not perm.can_view_page("IT Technician", "departments")
assert perm.can_view_page("IT Technician", "maintenance")
assert perm.can_view_page("Viewer", "departments")
assert not perm.can_view_page("Viewer", "users_roles")
assert perm.can_view_page("Viewer", "dashboard")  # always true, every role
print("   OK — Administrator/IT Manager/IT Technician/Viewer all see the right pages")

print("2. Write-access matrix...")
assert perm.can_write("Administrator", "directory")
assert perm.can_write("Administrator", "users")
assert perm.can_write("IT Manager", "assets")
assert not perm.can_write("IT Manager", "users")
assert perm.can_write("IT Technician", "maintenance")
assert not perm.can_write("IT Technician", "directory")
assert not perm.can_write("IT Technician", "invoices")
assert not any(perm.can_write("Viewer", area) for area in perm.WRITE_AREAS)
print("   OK — write access matches each role's documented scope")

print("3. Export + manage-users flags...")
assert perm.can_export("Administrator") and perm.can_export("IT Manager")
assert not perm.can_export("IT Technician") and not perm.can_export("Viewer")
assert perm.can_manage_users("Administrator")
assert not any(perm.can_manage_users(r) for r in ("IT Manager", "IT Technician", "Viewer"))
print("   OK — only Administrator/IT Manager export, only Administrator manages users")

with session_scope() as s:
    print("4. Service layer actually enforces this (not just the matrix dicts)...")
    depts = ds.list_departments(s)
    d = ds.create_department(s, "IT Manager", "IT Manager Test Dept", "x", "y")
    print("   OK — IT Manager CAN write to directory (Assets+Maintenance scope covers it)")
    ds.set_department_active(s, "IT Manager", d.id, False)

    try:
        user_service.create_user(s, "IT Manager", "nope", "Nope", "Viewer", "x")
        raise AssertionError("IT Manager should NOT be able to manage users")
    except perm.PermissionError:
        print("   OK — IT Manager blocked from user management at the service layer")

    try:
        asset_service.set_asset_active(s, "Viewer", asset_service.list_assets(s)[0]["id"], False)
        raise AssertionError("Viewer should never reach set_asset_active")
    except perm.PermissionError:
        print("   OK — Viewer blocked from asset writes at the service layer")

    print("5. Users: create, edit, guarded last-admin, reset password...")
    admins_before = [u for u in user_service.list_users(s) if u["role"] == "Administrator" and u["is_active"]]
    assert admins_before, "seed should include at least one active Administrator"

    new_user = user_service.create_user(s, "Administrator", "t.reviewer", "Test Reviewer",
                                         "Viewer", "TempPass123")
    audit_service.log_action(s, 1, "Create", "User", new_user.id, None, new_user.username)
    print(f"   OK — created user {new_user.username} ({new_user.role})")

    try:
        user_service.create_user(s, "IT Manager", "someone", "Someone", "Viewer", "x")
        raise AssertionError("IT Manager should not be able to create users")
    except perm.PermissionError:
        print("   OK — only Administrator can create users")

    try:
        user_service.create_user(s, "Administrator", "t.reviewer", "Dup", "Viewer", "x")
        raise AssertionError("duplicate username should be rejected")
    except user_service.UserServiceError as e:
        print(f"   OK — duplicate username rejected: {e}")

    user_service.update_user(s, "Administrator", new_user.id, "Test Reviewer II", "IT Technician")
    user_service.reset_password(s, "Administrator", new_user.id, "NewPass456")
    from app.services.auth_service import authenticate
    logged_in = authenticate(s, "t.reviewer", "NewPass456")
    assert logged_in is not None and logged_in.role == "IT Technician"
    print("   OK — updated role and reset password; new password authenticates")

    if len(admins_before) == 1:
        only_admin_id = admins_before[0]["id"]
        try:
            user_service.set_user_active(s, "Administrator", only_admin_id, False)
            raise AssertionError("should not be able to deactivate the last Administrator")
        except user_service.UserServiceError as e:
            print(f"   OK — last-Administrator guard held: {e}")
    else:
        print("   (more than one active Administrator in seed data — last-admin guard not exercised)")

    user_service.set_user_active(s, "Administrator", new_user.id, False)
    print("   OK — deactivated the test user")

    print("6. Audit log browser reflects what just happened...")
    # audit_logs is reseeded empty just like every other table — log a
    # Maintenance-entity entry explicitly so this test doesn't depend on
    # leftover state from a different script's run.
    any_maintenance = msvc.list_maintenance(s)[0]
    audit_service.log_action(s, 1, "StatusChange", "Maintenance", any_maintenance["id"],
                              "Received", "Assigned")

    logs = audit_log_service.list_audit_log(s, entity="User")
    assert any(log["new_value"] == "t.reviewer" for log in logs), "the create-user action should be logged"
    entities = audit_log_service.distinct_entities(s)
    assert "User" in entities and "Maintenance" in entities
    print(f"   OK — {len(logs)} User audit entries found, entities include {entities[:5]}...")

print("\nALL PHASE 8 CHECKS PASSED.")
