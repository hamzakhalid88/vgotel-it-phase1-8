from __future__ import annotations

from sqlalchemy import select

from PySide6.QtWidgets import QMessageBox, QWidget

from app.config import AppConfig
from app.db.base import session_scope
from app.db.models import Client, Department, Device
from app.services import asset_service, audit_service, permission_service
from app.services.asset_service import ASSET_STATUSES, DuplicateSerialError
from app.services.directory_service import InUseError
from app.ui.widgets.asset_detail_dialog import AssetDetailDialog
from app.ui.widgets.crud_list_page import CrudListPage
from app.ui.widgets.form_dialog import FieldSpec, FormDialog

COLUMNS = [
    ("Asset #", "asset_number"), ("Type", "asset_type"), ("Serial number", "serial_number"),
    ("Department", "department"), ("Assigned to", "client"), ("Repairs", "repair_count"),
]


def _choices() -> tuple[list[tuple], list[tuple], list[tuple]]:
    with session_scope() as s:
        depts = [(d.id, d.name) for d in s.scalars(
            select(Department).where(Department.is_active.is_(True)).order_by(Department.name)
        ).all()]
        clients = [(None, "\u2014 Unassigned \u2014")] + [(c.id, c.name) for c in s.scalars(
            select(Client).where(Client.is_active.is_(True)).order_by(Client.name)
        ).all()]
        devices = [(None, "\u2014 None \u2014")] + [(dv.id, dv.model) for dv in s.scalars(
            select(Device).order_by(Device.model)
        ).all()]
    return depts, clients, devices


def _fields() -> list[FieldSpec]:
    depts, clients, devices = _choices()
    return [
        FieldSpec("asset_type", "Asset type", required=True),
        FieldSpec("serial_number", "Serial number", required=True),
        FieldSpec("department_id", "Department", kind="combo", choices=depts),
        FieldSpec("client_id", "Assigned to", kind="combo", choices=clients),
        FieldSpec("device_id", "Device", kind="combo", choices=devices),
        FieldSpec("floor", "Floor"),
        FieldSpec("status", "Status", kind="combo",
                  choices=[(st, st) for st in ASSET_STATUSES]),
        FieldSpec("purchase_date", "Purchase date", kind="date"),
        FieldSpec("vendor", "Vendor"),
        FieldSpec("purchase_cost", "Purchase cost (Rs)", kind="number", min_value=0),
    ]


def build_assets_page(cfg: AppConfig, current_user_id: int, role: str, parent: QWidget | None = None) -> CrudListPage:
    def fetch_rows(search: str, status: str | None):
        with session_scope() as s:
            return asset_service.list_assets(s, search, status)

    def open_add_dialog() -> bool:
        dlg = FormDialog("Add asset", _fields(), parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        try:
            with session_scope() as s:
                a = asset_service.create_asset(
                    s, role, cfg.asset_prefix, v["asset_type"], v["serial_number"],
                    v["department_id"], v["client_id"], v["device_id"], v["floor"],
                    v["status"], v["purchase_date"], v["vendor"], v["purchase_cost"],
                )
                audit_service.log_action(
                    s, current_user_id, "Create", "Asset", a.id, None, a.asset_number
                )
        except DuplicateSerialError as e:
            QMessageBox.warning(parent, "Duplicate serial number", str(e))
            return False
        return True

    def open_edit_dialog(row: dict) -> bool:
        dlg = FormDialog(f"Edit asset {row['asset_number']}", _fields(), initial=row, parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        try:
            with session_scope() as s:
                asset_service.update_asset(
                    s, role, row["id"], v["asset_type"], v["serial_number"], v["department_id"],
                    v["client_id"], v["device_id"], v["floor"], v["status"],
                    v["purchase_date"], v["vendor"], v["purchase_cost"],
                )
                audit_service.log_action(
                    s, current_user_id, "Update", "Asset", row["id"],
                    row["asset_type"], v["asset_type"],
                )
        except DuplicateSerialError as e:
            QMessageBox.warning(parent, "Duplicate serial number", str(e))
            return False
        return True

    def toggle_active(row: dict):
        with session_scope() as s:
            asset_service.set_asset_active(s, role, row["id"], not row["is_active"])
            audit_service.log_action(
                s, current_user_id, "StatusChange", "Asset", row["id"],
                str(row["is_active"]), str(not row["is_active"]),
            )

    def on_view(row: dict):
        with session_scope() as s:
            detail = asset_service.get_asset_detail(s, row["id"])
        AssetDetailDialog(detail, parent=parent).exec()

    return CrudListPage(
        "Assets", "Every tracked asset, its assignment and repair history.",
        COLUMNS, fetch_rows, open_add_dialog, open_edit_dialog, toggle_active,
        on_view=on_view, filter_spec=("Status", ASSET_STATUSES),
        add_label="+ Add asset", can_write=permission_service.can_write(role, "assets"),
        parent=parent,
    )
