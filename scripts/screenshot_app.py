import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from app.config import load_config
from app.db.base import init_engine
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow
from app.ui.theme import QSS

app = QApplication(sys.argv)
app.setStyleSheet(QSS)

cfg = load_config()
init_engine(cfg.db_url)

out_dir = Path(__file__).resolve().parent.parent / "screenshots"
out_dir.mkdir(exist_ok=True)

# --- Login screen ---
login = LoginWindow(cfg.app_name, on_success=lambda *a: None)
login.resize(1000, 640)
login.show()
app.processEvents()
login.grab().save(str(out_dir / "login_screen.png"))
print("Saved", out_dir / "login_screen.png")
login.close()

# --- Dashboard (main shell) ---
win = MainWindow(cfg, 1, "Zeeshan Ahmed", "Administrator")
win.resize(1440, 900)
win.show()
app.processEvents()
app.processEvents()
win.grab().save(str(out_dir / "dashboard.png"))
print("Saved", out_dir / "dashboard.png")

from app.db.base import session_scope
from app.services import maintenance_service as msvc
from app.services import invoice_service as isvc

with session_scope() as s:
    seed_candidate = next(
        (m for m in msvc.list_maintenance(s) if m["status"] == "Completed"
         and m["invoice_number"] == "\u2014"),
        None,
    )
    if seed_candidate:
        isvc.generate_invoice(s, "Administrator", seed_candidate["id"], cfg.invoice_prefix)

# --- Phase 3 + Phase 4 + Phase 5 + Phase 6 + Phase 7 pages ---
for key in ("departments", "categories", "clients", "technicians", "assets", "devices",
            "maintenance", "repair_history", "gate_pass", "invoices", "reports"):
    win.sidebar._select(key)
    app.processEvents()
    win.grab().save(str(out_dir / f"{key}.png"))
    print("Saved", out_dir / f"{key}.png")

# --- Asset detail dialog, opened on a real seeded asset ---
from app.db.base import session_scope
from app.services import asset_service
from app.ui.widgets.asset_detail_dialog import AssetDetailDialog
from app.ui.widgets.maintenance_detail_dialog import MaintenanceDetailDialog

with session_scope() as s:
    first_id = asset_service.list_assets(s)[0]["id"]
    detail = asset_service.get_asset_detail(s, first_id)
dlg = AssetDetailDialog(detail)
dlg.show()
app.processEvents()
dlg.grab().save(str(out_dir / "asset_detail.png"))
print("Saved", out_dir / "asset_detail.png")

# --- Maintenance detail dialog (tabbed workflow view) on a real case ---
from app.services import maintenance_service as msvc
with session_scope() as s:
    mnt_id = msvc.list_maintenance(s)[0]["id"]
mdlg = MaintenanceDetailDialog(mnt_id, 1, "Administrator")
mdlg.show()
app.processEvents()
mdlg.grab().save(str(out_dir / "maintenance_detail.png"))
print("Saved", out_dir / "maintenance_detail.png")

# --- Maintenance detail for a Completed-but-uninvoiced case, to show the
# Generate invoice action and the warranty status badge together ---
with session_scope() as s:
    completed = next(
        (m for m in msvc.list_maintenance(s) if m["status"] == "Completed"
         and m["invoice_number"] == "\u2014"),
        None,
    )
if completed:
    mdlg2 = MaintenanceDetailDialog(completed["id"], 1, "Administrator")
    mdlg2.show()
    app.processEvents()
    mdlg2.grab().save(str(out_dir / "maintenance_detail_completed.png"))
    print("Saved", out_dir / "maintenance_detail_completed.png")

# --- Invoice card, opened on a real generated invoice ---
from app.services import invoice_service as isvc
from app.ui.pages.invoice_page import InvoiceCardDialog
with session_scope() as s:
    invoices = isvc.list_invoices(s)
    if not invoices and completed:
        isvc.generate_invoice(s, "Administrator", completed["id"], cfg.invoice_prefix)
        invoices = isvc.list_invoices(s)
if invoices:
    idlg = InvoiceCardDialog(invoices[0])
    idlg.show()
    app.processEvents()
    idlg.grab().save(str(out_dir / "invoice_card.png"))
    print("Saved", out_dir / "invoice_card.png")

# --- Two report viewers: one grouped-count report, one row-detail report ---
from app.ui.pages.reports_page import ReportViewerDialog
import app.services.report_service as rsvc

for key, label, runner in rsvc.REPORTS["Asset reports"]:
    if key == "assets_by_status":
        rdlg = ReportViewerDialog(key, label, runner, "Zeeshan Ahmed")
        rdlg.show()
        app.processEvents()
        rdlg.grab().save(str(out_dir / "report_assets_by_status.png"))
        print("Saved", out_dir / "report_assets_by_status.png")
        break

for key, label, runner in rsvc.REPORTS["Maintenance reports"]:
    if key == "technician_performance":
        rdlg2 = ReportViewerDialog(key, label, runner, "Zeeshan Ahmed")
        rdlg2.show()
        app.processEvents()
        rdlg2.grab().save(str(out_dir / "report_technician_performance.png"))
        print("Saved", out_dir / "report_technician_performance.png")
        break

# --- Users & roles (Administrator-only, now real) ---
from app.services import audit_service as _audit_svc
with session_scope() as s:
    _audit_svc.log_action(s, 1, "Login", "User", 1, None, "success")
    _audit_svc.log_action(s, 1, "Create", "Invoice", seed_candidate["id"] if seed_candidate else 1,
                           None, "invoice generated")
    if completed:
        _audit_svc.log_action(s, 1, "StatusChange", "Maintenance", completed["id"], "In Repair", "Completed")

win.sidebar._select("users_roles")
app.processEvents()
win.grab().save(str(out_dir / "users_roles.png"))
print("Saved", out_dir / "users_roles.png")

from PySide6.QtWidgets import QTabWidget
users_page = win._pages["users_roles"]
tabw = users_page.findChild(QTabWidget)
tabw.setCurrentIndex(1)  # Audit log tab
app.processEvents()
win.grab().save(str(out_dir / "audit_log.png"))
print("Saved", out_dir / "audit_log.png")
tabw.setCurrentIndex(0)

# --- The one page still genuinely on the roadmap ---
win.sidebar._select("settings")
app.processEvents()
win.grab().save(str(out_dir / "placeholder_page.png"))
print("Saved", out_dir / "placeholder_page.png")

# --- Role comparison: the same app, logged in as different roles ---
# IT Technician: narrow sidebar (no Directory/Invoices/Reports/Users)
tech_win = MainWindow(cfg, 3, "Bilal Khan", "IT Technician")
tech_win.resize(1440, 900)
tech_win.show()
app.processEvents()
tech_win.grab().save(str(out_dir / "role_it_technician_sidebar.png"))
print("Saved", out_dir / "role_it_technician_sidebar.png")

# Viewer: full sidebar visibility, but no write actions on a CRUD page
viewer_win = MainWindow(cfg, 4, "Front Desk Viewer", "Viewer")
viewer_win.resize(1440, 900)
viewer_win.show()
app.processEvents()
viewer_win.sidebar._select("departments")
app.processEvents()
viewer_win.grab().save(str(out_dir / "role_viewer_departments.png"))
print("Saved", out_dir / "role_viewer_departments.png")
