from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
    QVBoxLayout, QWidget,
)

from app.db.base import session_scope
from app.services import maintenance_service as msvc, permission_service
from app.ui.widgets.crud_list_page import CrudListPage

COLUMNS = [
    ("Gate pass #", "gate_pass_number"), ("Entry date", "entry_date_display"),
    ("Department", "department"), ("Employee", "employee_name"),
    ("Device", "device"), ("Technician", "technician"),
]


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


class GatePassCardDialog(QDialog):
    def __init__(self, row: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Gate pass {row['gate_pass_number']}")
        self.setStyleSheet("QDialog{background:#F1EFEA;}")
        self.resize(520, 660)

        page = QVBoxLayout(self)
        page.setContentsMargins(24, 24, 24, 24)

        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:#FFFFFF; border:1px solid #E7E5E0; border-radius:8px;}"
        )
        outer = QVBoxLayout(card)
        outer.setContentsMargins(30, 26, 30, 24)
        outer.setSpacing(0)

        # ---- letterhead ---------------------------------------------------
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

        gp_box = QVBoxLayout()
        gp_title = QLabel("GATE PASS")
        gp_title.setStyleSheet("color:#6B7178; font-size:11px; font-weight:700; letter-spacing:1px; border:none;")
        gp_title.setAlignment(Qt.AlignRight)
        gp_num = QLabel(row["gate_pass_number"])
        gp_num.setStyleSheet("color:#3B3FA1; font-size:16px; font-weight:700; border:none;")
        gp_num.setAlignment(Qt.AlignRight)
        gp_box.addWidget(gp_title)
        gp_box.addWidget(gp_num)
        head.addLayout(gp_box)
        outer.addLayout(head)

        outer.addSpacing(16)
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet("background:#14171A; border:none;")
        outer.addWidget(rule)
        outer.addSpacing(18)

        # ---- fields, two columns -------------------------------------------
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(16)
        fields = [
            ("Date", _fmt(row["entry_date"])), ("Asset #", row.get("asset_number", "\u2014")),
            ("Department", row["department"]), ("Employee", row["employee_name"]),
            ("Device / model", row["device"]), ("Technician", row["technician"]),
            ("Technician shop", row["technician_shop"]), ("Shop contact", row["technician_contact"]),
        ]
        for i, (label, value) in enumerate(fields):
            r, c = divmod(i, 2)
            grid.addWidget(_field(label, value), r, c)
        outer.addLayout(grid)
        outer.addSpacing(18)
        outer.addWidget(_field("Reason for gate pass", row["gate_pass_reason"]))
        outer.addSpacing(18)

        # ---- return window, boxed ------------------------------------------
        return_box = QFrame()
        return_box.setStyleSheet("QFrame{border:1px dashed #C7C3B8; border-radius:6px;}")
        rb = QHBoxLayout(return_box)
        rb.setContentsMargins(16, 12, 16, 12)
        rb.addWidget(_field("Expected return date", _fmt(row["expected_return_date"])))
        rb.addWidget(_field("Actual return date", _fmt(row["actual_return_date"])))
        outer.addWidget(return_box)

        outer.addSpacing(28)
        sig_row = QHBoxLayout()
        sig_row.setSpacing(30)
        for label, value in [("Authorized by", row["authorized_by"]), ("Security signature", "")]:
            box = QVBoxLayout()
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet("background:#C7C3B8; border:none;")
            box.addWidget(line)
            val = QLabel(value or "\u00A0")
            val.setStyleSheet("font-size:12px; font-weight:500; padding-top:3px; border:none;")
            lab = QLabel(label.upper())
            lab.setStyleSheet("color:#A8A49B; font-size:9.5px; font-weight:600; letter-spacing:0.5px; border:none;")
            box.addWidget(val)
            box.addWidget(lab)
            wrap = QWidget()
            wrap.setLayout(box)
            sig_row.addWidget(wrap)
        outer.addLayout(sig_row)

        outer.addSpacing(20)
        footer = QLabel(
            f"Valid only for the item and dates stated above. "
            f"Printed {dt.date.today().strftime('%d %b %Y')}."
        )
        footer.setStyleSheet("color:#A8A49B; font-size:10px; border:none;")
        footer.setWordWrap(True)
        outer.addWidget(footer)

        page.addWidget(card)


def build_gate_pass_page(role: str, parent: QWidget | None = None) -> CrudListPage:
    def fetch_rows(search: str, _status=None):
        with session_scope() as s:
            rows = msvc.list_maintenance(s, search)
        for r in rows:
            r["entry_date_display"] = r["entry_date"].strftime("%d %b %Y") if r["entry_date"] else "\u2014"
        return rows

    def explain_add(parent_widget) -> bool:
        QMessageBox.information(
            parent_widget, "Start from Maintenance",
            "A gate pass is generated automatically when you create a new "
            "maintenance case \u2014 open Maintenance \u2192 New maintenance.",
        )
        return False

    def on_view(row: dict):
        GatePassCardDialog(row, parent=parent).exec()

    return CrudListPage(
        "Gate pass", "Every gate pass issued for equipment leaving the building.",
        COLUMNS, fetch_rows,
        open_add_dialog=lambda: explain_add(parent),
        open_edit_dialog=lambda row: False,
        on_view=on_view, add_label="+ New (via Maintenance)",
        can_write=permission_service.can_write(role, "maintenance"),
        parent=parent,
    )
