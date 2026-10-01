from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.services.directory_service import InUseError


class CrudListPage(QWidget):
    """
    columns: list of (header_label, row_dict_key)
    fetch_rows(search, filter_value) -> list[dict]   (must include an "id" key;
                                                        filter_value is None unless filter_spec is set)
    open_add_dialog() -> bool                    True if something was created
    open_edit_dialog(row) -> bool                True if something changed
    toggle_active(row) -> None                   raises InUseError to block; only
                                                  wired up when rows carry "is_active"
    on_view(row) -> None                         optional read-only detail view;
                                                  when given, double-click and a
                                                  "View" action open it instead of Edit
    filter_spec: (label, [options])              optional second dropdown next to search
    can_write: bool                              Phase 8 — when False, hides the Add
                                                  button and every Edit/Deactivate/Delete
                                                  row action; View (if given) still shows.
                                                  Callers should also pass a role-checked
                                                  callable — this is UI-layer gating, the
                                                  service layer checks again regardless.
    """

    def __init__(
        self, title: str, subtitle: str,
        columns: list[tuple[str, str]],
        fetch_rows: Callable[[str, Optional[str]], list[dict]],
        open_add_dialog: Callable[[], bool],
        open_edit_dialog: Callable[[dict], bool],
        toggle_active: Optional[Callable[[dict], None]] = None,
        on_delete: Optional[Callable[[dict], None]] = None,
        on_view: Optional[Callable[[dict], None]] = None,
        filter_spec: Optional[tuple[str, list[str]]] = None,
        add_label: str = "+ Add",
        can_write: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.columns = columns
        self.fetch_rows = fetch_rows
        self.open_add_dialog = open_add_dialog
        self.open_edit_dialog = open_edit_dialog
        self.toggle_active = toggle_active
        self.on_delete = on_delete
        self.on_view = on_view
        self.can_write = can_write
        self._rows: list[dict] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 28, 40, 40)
        outer.setSpacing(16)

        head = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel(title)
        t.setObjectName("pageTitle")
        s = QLabel(subtitle)
        s.setObjectName("pageSub")
        title_box.addWidget(t)
        title_box.addWidget(s)
        head.addLayout(title_box, 1)

        if self.can_write:
            add_btn = QPushButton(add_label)
            add_btn.setStyleSheet(
                "QPushButton{padding:8px 16px; border-radius:4px; background:#14171A; color:white;"
                "font-size:13px; font-weight:600;}"
            )
            add_btn.clicked.connect(self._on_add)
            head.addWidget(add_btn, 0, Qt.AlignTop)
        outer.addLayout(head)

        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(f"Search {title.lower()}…")
        self.search_box.setMaximumWidth(320)
        self.search_box.setStyleSheet(
            "QLineEdit{padding:7px 10px; border:1px solid #E7E5E0; border-radius:4px; font-size:13px;}"
        )
        self.search_box.textChanged.connect(self.refresh)
        search_row.addWidget(self.search_box)

        self.filter_combo = None
        if filter_spec:
            label, options = filter_spec
            self.filter_combo = QComboBox()
            self.filter_combo.addItem(f"All {label.lower()}", None)
            for opt in options:
                self.filter_combo.addItem(opt, opt)
            self.filter_combo.setStyleSheet(
                "QComboBox{padding:6px 10px; border:1px solid #E7E5E0; border-radius:4px; font-size:13px;}"
            )
            self.filter_combo.currentIndexChanged.connect(self.refresh)
            search_row.addWidget(self.filter_combo)
        search_row.addStretch(1)
        outer.addLayout(search_row)

        col_count = len(columns) + (1 if toggle_active else 0) + 1  # + actions + edit
        self.table = QTableWidget(0, col_count)
        headers = [c[0] for c in columns] + (["Status"] if toggle_active else []) + ["Actions"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(col_count - 1, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(col_count - 1, 220)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setStyleSheet(
            "QTableWidget{border:1px solid #E7E5E0; border-radius:6px; gridline-color:#F0EEE9; font-size:13px;}"
            "QHeaderView::section{background:#FCFCFB; border:none; border-bottom:1px solid #E7E5E0;"
            "color:#6B7178; font-size:11px; font-weight:600; padding:8px;}"
        )
        self.table.cellDoubleClicked.connect(self._on_row_double_click)
        outer.addWidget(self.table, 1)

        self.refresh()

    def refresh(self):
        filter_value = self.filter_combo.currentData() if self.filter_combo else None
        self._rows = self.fetch_rows(self.search_box.text().strip(), filter_value)
        self.table.setRowCount(0)  # force-clear old cell widgets before repopulating (Qt ghost-widget fix)
        self.table.setRowCount(len(self._rows))

        for r, row in enumerate(self._rows):
            for c, (_, key) in enumerate(self.columns):
                val = row.get(key, "—")
                self.table.setItem(r, c, QTableWidgetItem(str(val)))

            col = len(self.columns)
            if self.toggle_active:
                active = row.get("is_active", True)
                item = QTableWidgetItem("Active" if active else "Inactive")
                from PySide6.QtGui import QColor
                item.setForeground(QColor("#2F6D4F" if active else "#A8A49B"))
                self.table.setItem(r, col, item)
                col += 1

            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(6)
            if self.on_view:
                view_btn = QPushButton("View")
                view_btn.setStyleSheet(self._link_btn_style("#14171A"))
                view_btn.clicked.connect(lambda checked=False, rr=row: self.on_view(rr))
                al.addWidget(view_btn)
            if self.can_write:
                edit_btn = QPushButton("Edit")
                edit_btn.setStyleSheet(self._link_btn_style("#3B3FA1"))
                edit_btn.clicked.connect(lambda checked=False, rr=row: self._on_edit(rr))
                al.addWidget(edit_btn)
                if self.toggle_active:
                    is_active = row.get("is_active", True)
                    toggle_btn = QPushButton("Deactivate" if is_active else "Activate")
                    toggle_btn.setStyleSheet(self._link_btn_style("#A63D3D" if is_active else "#2F6D4F"))
                    toggle_btn.clicked.connect(lambda checked=False, rr=row: self._on_toggle(rr))
                    al.addWidget(toggle_btn)
                if self.on_delete:
                    del_btn = QPushButton("Delete")
                    del_btn.setStyleSheet(self._link_btn_style("#A63D3D"))
                    del_btn.clicked.connect(lambda checked=False, rr=row: self._on_delete_row(rr))
                    al.addWidget(del_btn)
            al.addStretch(1)
            self.table.setCellWidget(r, col, actions)

    @staticmethod
    def _link_btn_style(color: str) -> str:
        return (
            f"QPushButton{{border:none; background:transparent; color:{color}; "
            f"font-size:12px; font-weight:600;}} QPushButton:hover{{text-decoration:underline;}}"
        )

    def _on_add(self):
        if self.open_add_dialog():
            self.refresh()

    def _on_edit(self, row: dict):
        if self.open_edit_dialog(row):
            self.refresh()

    def _on_row_double_click(self, row_idx: int, _col: int):
        if 0 <= row_idx < len(self._rows):
            row = self._rows[row_idx]
            if self.on_view:
                self.on_view(row)
            elif self.can_write:
                self._on_edit(row)

    def _on_toggle(self, row: dict):
        is_active = row.get("is_active", True)
        verb = "deactivate" if is_active else "reactivate"
        confirm = QMessageBox.question(
            self, f"{verb.capitalize()} record?",
            f"Are you sure you want to {verb} \u201c{row.get('name', 'this record')}\u201d?",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self.toggle_active(row)
        except InUseError as e:
            QMessageBox.warning(self, "Can't do that yet", str(e))
            return
        self.refresh()

    def _on_delete_row(self, row: dict):
        confirm = QMessageBox.question(
            self, "Delete record?",
            f"Delete \u201c{row.get('name', 'this record')}\u201d? This action cannot be easily undone.",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self.on_delete(row)
        except InUseError as e:
            QMessageBox.warning(self, "Can't delete this yet", str(e))
            return
        self.refresh()
