from __future__ import annotations

from sqlalchemy import select

from PySide6.QtWidgets import QWidget

from app.config import AppConfig
from app.db.base import session_scope
from app.db.models import Asset, Technician
from app.services import audit_service, maintenance_service as msvc, permission_service
from app.ui.widgets.crud_list_page import CrudListPage
from app.ui.widgets.form_dialog import FieldSpec, FormDialog
from app.ui.widgets.maintenance_detail_dialog import MaintenanceDetailDialog

COLUMNS = [
    ("Maintenance", "maintenance_number"), ("Device", "device"), ("Department", "department"),
    ("Technician", "technician"), ("Status", "display_status"), ("Cost", "cost_display"),
]

FILTER_STATUSES = msvc.WORKFLOW_STATUSES + ["Overdue"]


def _create_fields() -> list[FieldSpec]:
    with session_scope() as s:
        assets = [(a.id, f"{a.asset_number} \u2014 {a.asset_type}") for a in s.scalars(
            select(Asset).where(Asset.is_active.is_(True)).order_by(Asset.asset_number.desc())
        ).all()]
        techs = [(None, "\u2014 Assign later \u2014")] + [(t.id, t.name) for t in s.scalars(
            select(Technician).where(Technician.is_active.is_(True)).order_by(Technician.name)
        ).all()]
    return [
        FieldSpec("asset_id", "Asset", kind="combo", choices=assets, required=True),
        FieldSpec("issue", "Issue", kind="multiline", required=True),
        FieldSpec("technician_id", "Technician", kind="combo", choices=techs),
        FieldSpec("expected_return_date", "Expected return date", kind="date"),
        FieldSpec("gate_pass_reason", "Gate pass reason"),
        FieldSpec("authorized_by", "Authorized by"),
        FieldSpec("notes", "Notes", kind="multiline"),
    ]


def build_maintenance_page(cfg: AppConfig, current_user_id: int, role: str, parent: QWidget | None = None) -> CrudListPage:
    def fetch_rows(search: str, status: str | None):
        with session_scope() as s:
            rows = msvc.list_maintenance(s, search, status)
            for r in rows:
                r["cost_display"] = f"Rs {r['cost']:,.0f}" if r["cost"] else "\u2014"
            return rows

    def open_add_dialog() -> bool:
        dlg = FormDialog("New maintenance case", _create_fields(), parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        with session_scope() as s:
            m = msvc.create_maintenance(
                s, role, cfg.maintenance_prefix, cfg.gate_pass_prefix, v["asset_id"], v["issue"],
                v["technician_id"], v["expected_return_date"], v["gate_pass_reason"],
                v["authorized_by"], v["notes"],
            )
            audit_service.log_action(
                s, current_user_id, "Create", "Maintenance", m.id, None, m.maintenance_number
            )
        return True

    def on_view(row: dict):
        dlg = MaintenanceDetailDialog(row["id"], current_user_id, role, parent=parent)
        dlg.exec()
        if dlg.changed:
            page.refresh()

    def open_edit_dialog(row: dict) -> bool:
        # A maintenance case is advanced through its workflow, not freely
        # edited field-by-field — Edit opens the same tabbed detail view
        # as View. That dialog handles its own refresh, so this returns
        # False to avoid CrudListPage refreshing a second time.
        on_view(row)
        return False

    page = CrudListPage(
        "Maintenance", "Every repair case and where it stands in the workflow.",
        COLUMNS, fetch_rows, open_add_dialog, open_edit_dialog,
        on_view=on_view, filter_spec=("Status", FILTER_STATUSES),
        add_label="+ New maintenance", can_write=permission_service.can_write(role, "maintenance"),
        parent=parent,
    )
    return page
