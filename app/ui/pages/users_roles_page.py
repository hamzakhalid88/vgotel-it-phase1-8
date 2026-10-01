from __future__ import annotations

import datetime as dt

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from app.db.base import session_scope
from app.services import audit_log_service, audit_service, user_service
from app.services.permission_service import ROLES
from app.ui.widgets.crud_list_page import CrudListPage
from app.ui.widgets.form_dialog import FieldSpec, FormDialog

USER_COLUMNS = [
    ("Username", "username"), ("Full name", "full_name"), ("Role", "role"),
    ("Last login", "last_login_display"),
]


def _fmt_dt(d) -> str:
    return d.strftime("%d %b %Y %H:%M") if d else "\u2014"


def _build_users_tab(current_user_id: int, role: str, parent: QWidget) -> CrudListPage:
    def fetch_rows(search: str, _filter=None):
        with session_scope() as s:
            rows = user_service.list_users(s, search)
        for r in rows:
            r["last_login_display"] = _fmt_dt(r["last_login_at"])
        return rows

    def open_add_dialog() -> bool:
        dlg = FormDialog("Add user", [
            FieldSpec("username", "Username", required=True),
            FieldSpec("full_name", "Full name", required=True),
            FieldSpec("role", "Role", kind="combo", choices=[(r, r) for r in ROLES], required=True),
            FieldSpec("password", "Password", kind="password", required=True),
        ], parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        try:
            with session_scope() as s:
                u = user_service.create_user(s, role, v["username"], v["full_name"], v["role"], v["password"])
                audit_service.log_action(s, current_user_id, "Create", "User", u.id, None, u.username)
        except user_service.UserServiceError as e:
            QMessageBox.warning(parent, "Can't create that user", str(e))
            return False
        return True

    def open_edit_dialog(row: dict) -> bool:
        dlg = FormDialog(f"Edit {row['username']}", [
            FieldSpec("full_name", "Full name", required=True),
            FieldSpec("role", "Role", kind="combo", choices=[(r, r) for r in ROLES], required=True),
            FieldSpec("new_password", "New password (leave blank to keep unchanged)", kind="password"),
        ], initial=row, parent=parent)
        if dlg.exec() != FormDialog.Accepted:
            return False
        v = dlg.values
        try:
            with session_scope() as s:
                user_service.update_user(s, role, row["id"], v["full_name"], v["role"])
                if v.get("new_password"):
                    user_service.reset_password(s, role, row["id"], v["new_password"])
                audit_service.log_action(
                    s, current_user_id, "Update", "User", row["id"], row["role"], v["role"]
                )
        except user_service.UserServiceError as e:
            QMessageBox.warning(parent, "Can't save that", str(e))
            return False
        return True

    def toggle_active(row: dict):
        try:
            with session_scope() as s:
                user_service.set_user_active(s, role, row["id"], not row["is_active"])
                audit_service.log_action(
                    s, current_user_id, "StatusChange", "User", row["id"],
                    str(row["is_active"]), str(not row["is_active"]),
                )
        except user_service.UserServiceError as e:
            QMessageBox.warning(parent, "Can't do that", str(e))

    return CrudListPage(
        "Users", "Everyone with a login, their role, and when they last signed in.",
        USER_COLUMNS, fetch_rows, open_add_dialog, open_edit_dialog, toggle_active,
        add_label="+ Add user", parent=parent,
    )


class AuditLogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 20, 40, 30)
        outer.setSpacing(14)

        sub = QLabel("Every create, update, status change and login the system has recorded.")
        sub.setStyleSheet("color:#6B7178; font-size:13px;")
        outer.addWidget(sub)

        filt_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search audit log\u2026")
        self.search_box.setStyleSheet(
            "QLineEdit{padding:7px 10px; border:1px solid #E7E5E0; border-radius:4px; font-size:13px;}"
        )
        self.search_box.textChanged.connect(self.refresh)
        filt_row.addWidget(self.search_box, 1)

        self.entity_combo = QComboBox()
        self.entity_combo.addItem("All entities", None)
        self.entity_combo.setStyleSheet(
            "QComboBox{padding:6px 10px; border:1px solid #E7E5E0; border-radius:4px; font-size:13px;}"
        )
        self.entity_combo.currentIndexChanged.connect(self.refresh)
        filt_row.addWidget(self.entity_combo)

        self.action_combo = QComboBox()
        self.action_combo.addItem("All actions", None)
        for a in audit_log_service.ACTIONS:
            self.action_combo.addItem(a, a)
        self.action_combo.setStyleSheet(
            "QComboBox{padding:6px 10px; border:1px solid #E7E5E0; border-radius:4px; font-size:13px;}"
        )
        self.action_combo.currentIndexChanged.connect(self.refresh)
        filt_row.addWidget(self.action_combo)
        outer.addLayout(filt_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["When", "User", "Action", "Entity", "Change", "Computer"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setStyleSheet(
            "QTableWidget{border:1px solid #E7E5E0; border-radius:6px; gridline-color:#F0EEE9; font-size:12.5px;}"
            "QHeaderView::section{background:#FCFCFB; border:none; border-bottom:1px solid #E7E5E0;"
            "color:#6B7178; font-size:11px; font-weight:600; padding:7px;}"
        )
        outer.addWidget(self.table, 1)

        self._entities_loaded = False
        self.refresh()

    def refresh(self):
        with session_scope() as s:
            if not self._entities_loaded:
                for ent in audit_log_service.distinct_entities(s):
                    self.entity_combo.addItem(ent, ent)
                self._entities_loaded = True
            rows = audit_log_service.list_audit_log(
                s, self.search_box.text().strip(),
                entity=self.entity_combo.currentData(), action=self.action_combo.currentData(),
            )

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            change = f"{row['old_value']} \u2192 {row['new_value']}" \
                if row["old_value"] != "\u2014" or row["new_value"] != "\u2014" else "\u2014"
            values = [
                row["timestamp"].strftime("%d %b %Y %H:%M"), row["user"], row["action"],
                f"{row['entity']} #{row['record_id']}" if row["record_id"] else row["entity"],
                change, row["computer_name"],
            ]
            for c, val in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))


def build_users_roles_page(current_user_id: int, role: str, parent: QWidget | None = None) -> QWidget:
    host = QWidget(parent)
    layout = QVBoxLayout(host)
    layout.setContentsMargins(40, 28, 40, 0)
    layout.setSpacing(4)

    title = QLabel("Users & roles")
    title.setObjectName("pageTitle")
    layout.addWidget(title)
    layout.addSpacing(8)

    tabs = QTabWidget()
    users_tab = _build_users_tab(current_user_id, role, host)
    tabs.addTab(users_tab, "Users")
    audit_tab = AuditLogTab()
    tabs.addTab(audit_tab, "Audit log")
    layout.addWidget(tabs, 1)

    host.refresh = lambda: (users_tab.refresh(), audit_tab.refresh())
    return host
