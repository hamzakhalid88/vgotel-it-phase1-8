from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Optional

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)


@dataclass
class FieldSpec:
    key: str
    label: str
    kind: str = "text"          # "text" | "multiline" | "combo" | "date" | "number" | "password"
    choices: list[tuple[Any, str]] = field(default_factory=list)  # (value, display) for combo
    required: bool = False
    min_value: Optional[float] = None   # for kind="number", e.g. 0 to disallow negatives
    allow_blank_number: bool = True     # for kind="number": is "" a valid (None) value?


class FormDialog(QDialog):
    """Renders `fields` top to bottom, pre-filled from `initial`, and
    returns the entered values from `.values` after exec() if accepted."""

    def __init__(self, title: str, fields: list[FieldSpec], initial: Optional[dict] = None,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self._fields = fields
        self._inputs: dict[str, QWidget] = {}
        self.values: dict[str, Any] = {}
        initial = initial or {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 26, 28, 22)
        outer.setSpacing(4)

        heading = QLabel(title)
        heading.setStyleSheet("font-family:'Source Serif 4'; font-size:18px; font-weight:600;")
        outer.addWidget(heading)
        outer.addSpacing(14)

        for spec in fields:
            lbl = QLabel(spec.label + (" *" if spec.required else ""))
            lbl.setStyleSheet("font-size:11.5px; color:#6B7178; font-weight:600;")
            outer.addWidget(lbl)

            if spec.kind == "combo":
                w = QComboBox()
                for value, display in spec.choices:
                    w.addItem(display, value)
                current = initial.get(spec.key)
                if current is not None:
                    idx = w.findData(current)
                    if idx >= 0:
                        w.setCurrentIndex(idx)
                w.setStyleSheet(
                    "QComboBox{padding:7px 8px; border:1px solid #E7E5E0; border-radius:4px; font-size:13px;}"
                )
            elif spec.kind == "multiline":
                w = QTextEdit()
                w.setPlainText(str(initial.get(spec.key, "")))
                w.setFixedHeight(70)
                w.setStyleSheet(
                    "QTextEdit{border:1px solid #E7E5E0; border-radius:4px; font-size:13px; padding:6px;}"
                )
            elif spec.kind == "date":
                w = QDateEdit()
                w.setCalendarPopup(True)
                w.setDisplayFormat("yyyy-MM-dd")
                current = initial.get(spec.key)
                if isinstance(current, (dt.date, dt.datetime)):
                    w.setDate(QDate(current.year, current.month, current.day))
                else:
                    w.setDate(QDate.currentDate())
                w.setStyleSheet(
                    "QDateEdit{padding:7px 8px; border:1px solid #E7E5E0; border-radius:4px; font-size:13px;}"
                )
            else:
                init_val = initial.get(spec.key, "")
                if spec.kind == "number" and isinstance(init_val, (int, float)):
                    init_val = f"{init_val:g}"
                w = QLineEdit(str(init_val or ""))
                if spec.kind == "number":
                    w.setPlaceholderText("0")
                if spec.kind == "password":
                    w.setEchoMode(QLineEdit.Password)
                w.setStyleSheet(
                    "QLineEdit{padding:8px 9px; border:1px solid #E7E5E0; border-radius:4px; font-size:13px;}"
                    "QLineEdit:focus{border-color:#3B3FA1;}"
                )

            self._inputs[spec.key] = w
            outer.addWidget(w)
            outer.addSpacing(10)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color:#A63D3D; font-size:12px;")
        self.error_label.setWordWrap(True)
        outer.addWidget(self.error_label)
        outer.addSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            "QPushButton{padding:8px 16px; border:1px solid #E7E5E0; border-radius:4px; font-size:13px;}"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(
            "QPushButton{padding:8px 18px; border-radius:4px; background:#14171A; color:white;"
            "font-size:13px; font-weight:600;}"
        )
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        outer.addLayout(btn_row)

    def _on_save(self):
        values = {}
        for spec in self._fields:
            w = self._inputs[spec.key]
            if isinstance(w, QComboBox):
                val = w.currentData()
            elif isinstance(w, QTextEdit):
                val = w.toPlainText().strip()
            elif isinstance(w, QDateEdit):
                qd = w.date()
                val = dt.date(qd.year(), qd.month(), qd.day())
            elif spec.kind == "number":
                raw = w.text().strip()
                if not raw:
                    if spec.required:
                        self.error_label.setText(f"{spec.label} is required.")
                        return
                    val = None if spec.allow_blank_number else 0
                else:
                    try:
                        val = float(raw)
                    except ValueError:
                        self.error_label.setText(f"{spec.label} must be a number.")
                        return
                    if spec.min_value is not None and val < spec.min_value:
                        self.error_label.setText(f"{spec.label} cannot be less than {spec.min_value:g}.")
                        return
            else:
                val = w.text().strip()

            if spec.required and spec.kind != "number" and not val:
                self.error_label.setText(f"{spec.label} is required.")
                return
            values[spec.key] = val

        self.values = values
        self.accept()
