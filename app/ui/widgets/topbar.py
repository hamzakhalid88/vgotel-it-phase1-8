from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget


class TopBar(QWidget):
    def __init__(self, user_full_name: str, user_role: str, notification_count: int, parent=None):
        super().__init__(parent)
        self.setObjectName("topbar")
        self.setFixedHeight(66)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 0, 40, 0)
        layout.setSpacing(20)

        self.crumb_label = QLabel("Home / <b>Dashboard</b>")
        self.crumb_label.setStyleSheet("font-size:13px; color:#6B7178;")
        layout.addWidget(self.crumb_label)

        search = QLineEdit()
        search.setObjectName("searchBox")
        search.setPlaceholderText("Search assets, maintenance, invoices…")
        search.setMaximumWidth(380)
        layout.addWidget(search, 1)

        bell = QLabel(f"\U0001F514 {notification_count}" if notification_count else "\U0001F514")
        bell.setStyleSheet("font-size:14px; color:#6B7178;")
        layout.addWidget(bell)

        divider = QLabel()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background:#E7E5E0;")
        divider.setFixedHeight(30)
        layout.addWidget(divider)

        user_box = QWidget()
        user_l = QVBoxLayout(user_box)
        user_l.setContentsMargins(6, 0, 0, 0)
        user_l.setSpacing(0)
        uname = QLabel(user_full_name)
        uname.setStyleSheet("font-size:13px; font-weight:600;")
        urole = QLabel(user_role)
        urole.setStyleSheet("font-size:11.5px; color:#6B7178;")
        user_l.addWidget(uname)
        user_l.addWidget(urole)
        layout.addWidget(user_box)

    def set_breadcrumb(self, page_title: str):
        self.crumb_label.setText(f"Home / <b>{page_title}</b>")
