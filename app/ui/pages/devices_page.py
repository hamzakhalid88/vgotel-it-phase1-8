from __future__ import annotations

from sqlalchemy import select

from PySide6.QtWidgets import QWidget

from app.db.base import session_scope
from app.db.models import Category, Department
from app.services import audit_service, device_service, permission_service
from app.services.device_service import DEVICE_STATUSES
from app.ui.widgets.crud_list_page import CrudListPage
from app.ui.widgets.form_dialog import FieldSpec, FormDialog

COLUMNS = [
    ("Model", "model"), ("Category", "category"), ("Department", "department"),
    ("Serial number", "serial_number"), ("Status", "status"),
]


def _fields() -> list[FieldSpec]:
    with session_scope() as s:
        cats = [(c.id, c.name) for c in s.scalars(select(Category).order_by(Category.name)).all()]
        depts = [(d.id, d.name) for d in s.scalars(
            select(Department).where(Department.is_active.is_(True)).order_by(Department.name)
        ).all()]
    return [
        FieldSpec("model", "Model", required=True),
        FieldSpec("category_id", "Category", kind="combo", choices=cats),
        FieldSpec("department_id", "Department", kind="combo", choices=depts),
        FieldSpec("serial_number", "Serial number"),
        FieldSpec("purchase_date", "Purchase date", kind="date"),
        FieldSpec("status", "Status", kind="combo", choices=[(s, s) for s in DEVICE_STATUSES]),
    ]


def build_devices_page(current_user_id: int, role: str, parent: QWidget | None = None) -> CrudListPage:
    def fetch_rows(search: str, status: str | None):
        with session_scope() as s:
            return device_service.list_devices(s, search, status)

    def open_add_dialog() -> bool:
        dlg = FormDialog("Add device", _fields(), parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            d = device_service.create_device(
                s, role, v["model"], v["category_id"], v["department_id"],
                v["serial_number"], v["purchase_date"], v["status"],
            )
            audit_service.log_action(s, current_user_id, "Create", "Device", d.id, None, v["model"])
        return True

    def open_edit_dialog(row: dict) -> bool:
        dlg = FormDialog(f"Edit {row['model']}", _fields(), initial=row, parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            device_service.update_device(
                s, role, row["id"], v["model"], v["category_id"], v["department_id"],
                v["serial_number"], v["purchase_date"], v["status"],
            )
            audit_service.log_action(
                s, current_user_id, "Update", "Device", row["id"], row["model"], v["model"]
            )
        return True

    def on_delete(row: dict):
        with session_scope() as s:
            device_service.delete_device(s, role, row["id"])
            audit_service.log_action(s, current_user_id, "Delete", "Device", row["id"], row["model"], None)

    return CrudListPage(
        "Devices", "The device catalog assets are linked to.",
        COLUMNS, fetch_rows, open_add_dialog, open_edit_dialog,
        on_delete=on_delete, filter_spec=("Status", DEVICE_STATUSES),
        add_label="+ Add device", can_write=permission_service.can_write(role, "devices"),
        parent=parent,
    )
