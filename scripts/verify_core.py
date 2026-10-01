"""Run with: python -m scripts.verify_core   (from the project root)

Exercises config -> db -> services end to end against the local sqlite
dev database and prints real results. This is the "test it before moving
on" step the brief itself asks for in section 74.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config
from app.db.base import init_engine, session_scope
from app.db.seed import seed
from app.services import dashboard_service, numbering_service
from app.services.auth_service import authenticate

print("1. Loading config...")
cfg = load_config()
print(f"   app_name={cfg.app_name!r} dialect={cfg.dialect!r} db_url={cfg.db_url!r}")
assert cfg.dialect == "sqlite"

print("2. Seeding local dev database...")
seed()

print("3. Re-initialising engine for a fresh session (simulates app startup)...")
init_engine(cfg.db_url)

with session_scope() as s:
    print("4. Testing authenticate()...")
    user = authenticate(s, "admin", "Admin@123")
    assert user is not None, "expected admin login to succeed"
    print(f"   OK — logged in as {user.full_name} ({user.role})")

    bad = authenticate(s, "admin", "wrong-password")
    assert bad is None, "wrong password must not authenticate"
    print("   OK — wrong password correctly rejected")

    print("5. Testing numbering_service (concurrency-safe sequences)...")
    a1 = numbering_service.next_asset_number(s, cfg.asset_prefix)
    a2 = numbering_service.next_asset_number(s, cfg.asset_prefix)
    print(f"   {a1} -> {a2}")
    assert a1 != a2

    mnt = numbering_service.next_maintenance_number(s, cfg.maintenance_prefix)
    gp = numbering_service.next_gate_pass_number(s, cfg.gate_pass_prefix)
    inv = numbering_service.next_invoice_number(s, cfg.invoice_prefix)
    print(f"   {mnt}   {gp}   {inv}")

    print("6. Testing dashboard_service (real aggregate queries)...")
    kpis = dashboard_service.get_kpis(s, cfg.warranty_alert_days)
    print(f"   KPIs: {kpis}")
    assert kpis["total_assets"] > 0

    trend = dashboard_service.get_monthly_cost_trend(s)
    print(f"   Monthly cost trend: {trend}")

    dist = dashboard_service.get_asset_status_distribution(s)
    print(f"   Asset status distribution: {dist}")

    by_dept = dashboard_service.get_repairs_by_department(s)
    print(f"   Repairs by department: {by_dept}")

    warranty = dashboard_service.get_warranty_expiring(s, cfg.warranty_alert_days)
    print(f"   Warranty expiring soon ({len(warranty)} items):")
    for w in warranty:
        print(f"     - {w}")

    recent = dashboard_service.get_recent_maintenance(s)
    print(f"   Recent maintenance ({len(recent)} rows):")
    for r in recent:
        print(f"     - {r}")

print("\nALL CHECKS PASSED.")
