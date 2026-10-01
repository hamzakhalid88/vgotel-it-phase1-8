from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.db.base import session_scope
from app.services import audit_service, directory_service, permission_service
from app.ui.widgets.crud_list_page import CrudListPage
from app.ui.widgets.form_dialog import FieldSpec, FormDialog

COLUMNS = [("Category", "name"), ("Description", "description"),
           ("Devices", "devices"), ("Maintenance", "maintenance")]

FIELDS = [
    FieldSpec("name", "Category name", required=True),
    FieldSpec("description", "Description", kind="multiline"),
]


def build_categories_page(current_user_id: int, role: str, parent: QWidget | None = None) -> CrudListPage:
    def fetch_rows(search: str, _filter=None):
        with session_scope() as s:
            return directory_service.list_categories(s, search)

    def open_add_dialog() -> bool:
        dlg = FormDialog("Add category", FIELDS, parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            c = directory_service.create_category(s, role, v["name"], v["description"])
            audit_service.log_action(s, current_user_id, "Create", "Category", c.id, None, v["name"])
        return True

    def open_edit_dialog(row: dict) -> bool:
        dlg = FormDialog("Edit category", FIELDS, initial=row, parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            directory_service.update_category(s, role, row["id"], v["name"], v["description"])
            audit_service.log_action(
                s, current_user_id, "Update", "Category", row["id"], row["name"], v["name"]
            )
        return True

    def on_delete(row: dict):
        with session_scope() as s:
            directory_service.delete_category(s, role, row["id"])
            audit_service.log_action(s, current_user_id, "Delete", "Category", row["id"], row["name"], None)

    return CrudListPage(
        "Categories", "Device categories and how many devices and maintenance records use each.",
        COLUMNS, fetch_rows, open_add_dialog, open_edit_dialog,
        on_delete=on_delete, add_label="+ Add category",
        can_write=permission_service.can_write(role, "directory"), parent=parent,
    )
