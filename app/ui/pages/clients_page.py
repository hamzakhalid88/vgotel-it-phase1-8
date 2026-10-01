from __future__ import annotations

from sqlalchemy import select

from PySide6.QtWidgets import QWidget

from app.db.base import session_scope
from app.db.models import Department
from app.services import audit_service, directory_service, permission_service
from app.ui.widgets.crud_list_page import CrudListPage
from app.ui.widgets.form_dialog import FieldSpec, FormDialog

COLUMNS = [
    ("Name", "name"), ("Department", "department"), ("Designation", "designation"),
    ("Phone", "phone"), ("Email", "email"), ("Assets", "assigned_assets"),
]


def _department_choices() -> list[tuple[int, str]]:
    with session_scope() as s:
        depts = s.scalars(select(Department).where(Department.is_active.is_(True)).order_by(Department.name)).all()
        return [(d.id, d.name) for d in depts]


def _fields() -> list[FieldSpec]:
    return [
        FieldSpec("name", "Full name", required=True),
        FieldSpec("department_id", "Department", kind="combo", choices=_department_choices()),
        FieldSpec("designation", "Designation"),
        FieldSpec("phone", "Phone"),
        FieldSpec("email", "Email"),
    ]


def build_clients_page(current_user_id: int, role: str, parent: QWidget | None = None) -> CrudListPage:
    def fetch_rows(search: str, _filter=None):
        with session_scope() as s:
            return directory_service.list_clients(s, search)

    def open_add_dialog() -> bool:
        dlg = FormDialog("Add client / employee", _fields(), parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            c = directory_service.create_client(
                s, role, v["name"], v["department_id"], v["phone"], v["email"], v["designation"]
            )
            audit_service.log_action(s, current_user_id, "Create", "Client", c.id, None, v["name"])
        return True

    def open_edit_dialog(row: dict) -> bool:
        dlg = FormDialog("Edit client / employee", _fields(), initial=row, parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            directory_service.update_client(
                s, role, row["id"], v["name"], v["department_id"], v["phone"], v["email"], v["designation"]
            )
            audit_service.log_action(
                s, current_user_id, "Update", "Client", row["id"], row["name"], v["name"]
            )
        return True

    def toggle_active(row: dict):
        with session_scope() as s:
            directory_service.set_client_active(s, role, row["id"], not row["is_active"])
            audit_service.log_action(
                s, current_user_id, "StatusChange", "Client", row["id"],
                str(row["is_active"]), str(not row["is_active"]),
            )

    return CrudListPage(
        "Clients", "Employees assets can be assigned to, and how many they currently hold.",
        COLUMNS, fetch_rows, open_add_dialog, open_edit_dialog, toggle_active,
        add_label="+ Add client", can_write=permission_service.can_write(role, "directory"),
        parent=parent,
    )
