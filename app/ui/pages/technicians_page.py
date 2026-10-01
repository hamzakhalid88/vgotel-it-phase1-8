from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.db.base import session_scope
from app.services import audit_service, directory_service, permission_service
from app.ui.widgets.crud_list_page import CrudListPage
from app.ui.widgets.form_dialog import FieldSpec, FormDialog

COLUMNS = [
    ("Name", "name"), ("Shop", "shop_name"), ("Phone", "phone"),
    ("Total jobs", "total_jobs"), ("Completed", "completed_jobs"),
]

FIELDS = [
    FieldSpec("name", "Technician name", required=True),
    FieldSpec("phone", "Phone"),
    FieldSpec("email", "Email"),
    FieldSpec("address", "Address", kind="multiline"),
    FieldSpec("shop_name", "Shop name"),
    FieldSpec("shop_contact", "Shop contact"),
]


def build_technicians_page(current_user_id: int, role: str, parent: QWidget | None = None) -> CrudListPage:
    def fetch_rows(search: str, _filter=None):
        with session_scope() as s:
            rows = directory_service.list_technicians(s, search)
            for r in rows:
                r["total_cost_display"] = f"Rs {r['total_cost']:,.0f}"
            return rows

    def open_add_dialog() -> bool:
        dlg = FormDialog("Add technician", FIELDS, parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            t = directory_service.create_technician(
                s, role, v["name"], v["phone"], v["email"], v["address"], v["shop_name"], v["shop_contact"]
            )
            audit_service.log_action(s, current_user_id, "Create", "Technician", t.id, None, v["name"])
        return True

    def open_edit_dialog(row: dict) -> bool:
        dlg = FormDialog("Edit technician", FIELDS, initial=row, parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            directory_service.update_technician(
                s, role, row["id"], v["name"], v["phone"], v["email"], v["address"],
                v["shop_name"], v["shop_contact"],
            )
            audit_service.log_action(
                s, current_user_id, "Update", "Technician", row["id"], row["name"], v["name"]
            )
        return True

    def toggle_active(row: dict):
        with session_scope() as s:
            directory_service.set_technician_active(s, role, row["id"], not row["is_active"])
            audit_service.log_action(
                s, current_user_id, "StatusChange", "Technician", row["id"],
                str(row["is_active"]), str(not row["is_active"]),
            )

    return CrudListPage(
        "Technicians", "Shop contacts, live job counts and repair spend per technician.",
        COLUMNS, fetch_rows, open_add_dialog, open_edit_dialog, toggle_active,
        add_label="+ Add technician", can_write=permission_service.can_write(role, "directory"),
        parent=parent,
    )
