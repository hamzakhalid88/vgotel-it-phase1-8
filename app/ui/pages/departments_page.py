from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from app.db.base import session_scope
from app.services import audit_service, directory_service, permission_service
from app.ui.widgets.crud_list_page import CrudListPage
from app.ui.widgets.form_dialog import FieldSpec, FormDialog

COLUMNS = [
    ("Department", "name"), ("Location", "location"), ("Phone", "phone"),
    ("Assets", "assets"), ("Devices", "devices"), ("Clients", "clients"),
    ("Maintenance", "maintenance"),
]

FIELDS = [
    FieldSpec("name", "Department name", required=True),
    FieldSpec("location", "Location"),
    FieldSpec("phone", "Phone"),
]


def build_departments_page(current_user_id: int, role: str, parent: QWidget | None = None) -> CrudListPage:
    def fetch_rows(search: str, _filter=None):
        with session_scope() as s:
            return directory_service.list_departments(s, search)

    def open_add_dialog() -> bool:
        dlg = FormDialog("Add department", FIELDS, parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            d = directory_service.create_department(s, role, v["name"], v["location"], v["phone"])
            audit_service.log_action(s, current_user_id, "Create", "Department", d.id, None, v["name"])
        return True

    def open_edit_dialog(row: dict) -> bool:
        dlg = FormDialog("Edit department", FIELDS, initial=row, parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            directory_service.update_department(s, role, row["id"], v["name"], v["location"], v["phone"])
            audit_service.log_action(
                s, current_user_id, "Update", "Department", row["id"], row["name"], v["name"]
            )
        return True

    def toggle_active(row: dict):
        with session_scope() as s:
            directory_service.set_department_active(s, role, row["id"], not row["is_active"])
            audit_service.log_action(
                s, current_user_id, "StatusChange", "Department", row["id"],
                str(row["is_active"]), str(not row["is_active"]),
            )

    return CrudListPage(
        "Departments", "Locations, phones and how much each department has on record.",
        COLUMNS, fetch_rows, open_add_dialog, open_edit_dialog, toggle_active,
        add_label="+ Add department", can_write=permission_service.can_write(role, "directory"),
        parent=parent,
    )
