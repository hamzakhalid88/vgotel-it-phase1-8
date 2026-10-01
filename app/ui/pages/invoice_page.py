from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget,
)

from app.config import AppConfig
from app.db.base import session_scope
from app.services import audit_service, invoice_service as isvc, permission_service
from app.ui.widgets.crud_list_page import CrudListPage
from app.ui.widgets.form_dialog import FieldSpec, FormDialog

COLUMNS = [
    ("Invoice #", "invoice_number"), ("Date", "date_display"), ("Department", "department"),
    ("Device", "device"), ("Technician", "technician"), ("Cost", "cost_display"),
    ("Warranty", "warranty_status"),
]

WARRANTY_COLORS = {"Active": "#2F6D4F", "Expiring soon": "#A66A1D", "Expired": "#A63D3D"}


def _fmt(d) -> str:
    return d.strftime("%d %b %Y") if d else "\u2014"


def _field(label: str, value: str) -> QWidget:
    row = QWidget()
    l = QVBoxLayout(row)
    l.setContentsMargins(0, 0, 0, 0)
    l.setSpacing(2)
    lab = QLabel(label.upper())
    lab.setStyleSheet("color:#A8A49B; font-size:10px; font-weight:600; letter-spacing:0.5px;")
    val = QLabel(value or "\u2014")
    val.setStyleSheet("font-size:13.5px; font-weight:500; color:#14171A;")
    val.setWordWrap(True)
    l.addWidget(lab)
    l.addWidget(val)
    return row


class InvoiceCardDialog(QDialog):
    def __init__(self, row: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Invoice {row['invoice_number']}")
        self.setStyleSheet("QDialog{background:#F1EFEA;}")
        self.resize(520, 620)

        page = QVBoxLayout(self)
        page.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setStyleSheet("QFrame{background:#FFFFFF; border:1px solid #E7E5E0; border-radius:8px;}")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(30, 26, 30, 24)
        outer.setSpacing(0)

        head = QHBoxLayout()
        brand_box = QVBoxLayout()
        brand = QLabel("Vgotel")
        brand.setStyleSheet(
            "font-family:'Source Serif 4'; font-style:italic; font-size:19px; font-weight:600; border:none;"
        )
        brand_sub = QLabel("Asset & Maintenance Register")
        brand_sub.setStyleSheet("color:#6B7178; font-size:10.5px; border:none;")
        brand_box.addWidget(brand)
        brand_box.addWidget(brand_sub)
        head.addLayout(brand_box, 1)

        inv_box = QVBoxLayout()
        inv_title = QLabel("INVOICE")
        inv_title.setStyleSheet("color:#6B7178; font-size:11px; font-weight:700; letter-spacing:1px; border:none;")
        inv_title.setAlignment(Qt.AlignRight)
        inv_num = QLabel(row["invoice_number"])
        inv_num.setStyleSheet("color:#3B3FA1; font-size:16px; font-weight:700; border:none;")
        inv_num.setAlignment(Qt.AlignRight)
        inv_box.addWidget(inv_title)
        inv_box.addWidget(inv_num)
        head.addLayout(inv_box)
        outer.addLayout(head)

        outer.addSpacing(16)
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet("background:#14171A; border:none;")
        outer.addWidget(rule)
        outer.addSpacing(18)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)
        fields = [
            ("Date", _fmt(row["date"])), ("Maintenance #", row["maintenance_number"]),
            ("Department", row["department"]), ("Device / model", row["device"]),
            ("Technician", row["technician"]), ("Shop", row["technician_shop"]),
        ]
        for i, (label, value) in enumerate(fields):
            r, c = divmod(i, 2)
            grid.addWidget(_field(label, value), r, c)
        outer.addLayout(grid)
        outer.addSpacing(18)

        cost_box = QFrame()
        cost_box.setStyleSheet("QFrame{border:1px dashed #C7C3B8; border-radius:6px;}")
        cb = QHBoxLayout(cost_box)
        cb.setContentsMargins(16, 12, 16, 12)
        cb.addWidget(_field("Repair cost", f"Rs {row['cost']:,.0f}" if row["cost"] else "\u2014"))
        w_status = row["warranty_status"]
        w_text = w_status if w_status == "\u2014" else (
            f"{w_status} \u2014 until {_fmt(row['warranty_until'])}"
        )
        cb.addWidget(_field("Warranty", w_text))
        outer.addWidget(cost_box)
        outer.addSpacing(18)
        outer.addWidget(_field("Notes", row["notes"]))

        outer.addSpacing(20)
        footer = QLabel(
            f"This invoice reflects repair work completed and recorded in the "
            f"maintenance system. Printed {dt.date.today().strftime('%d %b %Y')}."
        )
        footer.setStyleSheet("color:#A8A49B; font-size:10px; border:none;")
        footer.setWordWrap(True)
        outer.addWidget(footer)

        page.addWidget(card)


def build_invoice_page(cfg: AppConfig, current_user_id: int, role: str, parent: QWidget | None = None) -> CrudListPage:
    def fetch_rows(search: str, _status=None):
        with session_scope() as s:
            rows = isvc.list_invoices(s, search)
        for r in rows:
            r["date_display"] = _fmt(r["date"])
            r["cost_display"] = f"Rs {r['cost']:,.0f}" if r["cost"] else "\u2014"
        return rows

    def open_add_dialog() -> bool:
        with session_scope() as s:
            candidates = isvc.list_uninvoiced_completed(s)
        if not candidates:
            QMessageBox.information(
                parent, "Nothing to invoice",
                "Every completed case already has an invoice. Complete a "
                "maintenance case first to generate a new one.",
            )
            return False

        choices = [(c["id"], f"{c['maintenance_number']} \u2014 {c['device']} "
                              f"(Rs {c['cost']:,.0f})") for c in candidates]
        dlg = FormDialog("Generate invoice", [
            FieldSpec("maintenance_id", "Completed case", kind="combo", choices=choices, required=True)
        ], parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        with session_scope() as s:
            number = isvc.generate_invoice(s, role, dlg.values["maintenance_id"], cfg.invoice_prefix)
            audit_service.log_action(s, current_user_id, "Create", "Invoice",
                                      dlg.values["maintenance_id"], None, number)
        return True

    def on_view(row: dict):
        InvoiceCardDialog(row, parent=parent).exec()

    return CrudListPage(
        "Invoices", "Every invoice generated from a completed repair, with live warranty status.",
        COLUMNS, fetch_rows,
        open_add_dialog=open_add_dialog,
        open_edit_dialog=lambda row: False,
        on_view=on_view, add_label="+ Generate invoice",
        can_write=permission_service.can_write(role, "invoices"),
        parent=parent,
    )
