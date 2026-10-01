"""Run with: python -m scripts.verify_phase6   (from the project root)"""
import datetime as dt
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config
from app.db.base import init_engine, session_scope
from app.services import attachment_service, invoice_service as isvc
from app.services import maintenance_service as msvc

ADMIN = "Administrator"

cfg = load_config()
init_engine(cfg.db_url)

with session_scope() as s:
    print("1. Warranty status helper...")
    today = dt.date.today()
    assert isvc.warranty_status(None) == "\u2014"
    assert isvc.warranty_status(today - dt.timedelta(days=1)) == "Expired"
    assert isvc.warranty_status(today + dt.timedelta(days=10)) == "Expiring soon"
    assert isvc.warranty_status(today + dt.timedelta(days=90)) == "Active"
    print("   OK — Expired / Expiring soon / Active all correct")

    print("2. Can't invoice a case that isn't Completed yet...")
    open_case = next(m for m in msvc.list_maintenance(s) if m["status"] in ("Received", "Assigned", "In Repair"))
    try:
        isvc.generate_invoice(s, ADMIN, open_case["id"], cfg.invoice_prefix)
        raise AssertionError("expected InvoiceError for a case that isn't Completed")
    except isvc.InvoiceError as e:
        print(f"   OK — correctly blocked: {e}")

    print("3. Generate an invoice for a real completed case...")
    candidates = isvc.list_uninvoiced_completed(s)
    assert candidates, "seed should include at least one completed-but-uninvoiced case"
    target = candidates[0]
    number = isvc.generate_invoice(s, ADMIN, target["id"], cfg.invoice_prefix)
    print(f"   OK — generated {number} for {target['maintenance_number']}")
    assert number.startswith(cfg.invoice_prefix)

    again = isvc.generate_invoice(s, ADMIN, target["id"], cfg.invoice_prefix)
    assert again == number
    print("   OK — calling it again is idempotent, not a duplicate")

    detail = isvc.get_invoice_detail(s, target["id"])
    print(f"   OK — detail loads: warranty_status={detail['warranty_status']}")

    print("4. Attachments: store, resolve, remove...")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(b"not a real png, just bytes for the test")
        tmp_path = tmp.name

    rel_path = attachment_service.store_bill_image(tmp_path, target["maintenance_number"], dt.date.today())
    full_path = attachment_service.resolve(rel_path)
    assert full_path.exists()
    print(f"   OK — stored at {rel_path}")

    msvc.set_bill_image(s, ADMIN, target["id"], rel_path)
    reloaded = msvc.get_maintenance_detail(s, target["id"])
    assert reloaded["bill_image"] == rel_path
    print("   OK — bill_image saved on the maintenance record")

    old = msvc.clear_bill_image(s, ADMIN, target["id"])
    attachment_service.remove_bill_image(old)
    assert not full_path.exists()
    print("   OK — cleared and the file removed")

    Path(tmp_path).unlink(missing_ok=True)

    print("5. Phase 8 spot-check: an IT Manager can invoice, an IT Technician cannot...")
    from app.services.permission_service import PermissionError as PermError
    candidates2 = isvc.list_uninvoiced_completed(s)
    if candidates2:
        ok_number = isvc.generate_invoice(s, "IT Manager", candidates2[0]["id"], cfg.invoice_prefix)
        print(f"   OK — IT Manager generated {ok_number}")
    try:
        target_id = candidates2[1]["id"] if len(candidates2) > 1 else target["id"]
        isvc.generate_invoice(s, "IT Technician", target_id, cfg.invoice_prefix)
        raise AssertionError("expected PermissionError for IT Technician generating an invoice")
    except PermError as e:
        print(f"   OK — correctly blocked: {e}")

print("\nALL PHASE 6 CHECKS PASSED.")
