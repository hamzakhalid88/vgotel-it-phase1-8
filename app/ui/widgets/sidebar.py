from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from app.services import permission_service

NAV_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Overview", [("dashboard", "Dashboard")]),
    ("Asset management", [("assets", "Assets"), ("devices", "Devices"), ("categories", "Categories")]),
    ("Operations", [
        ("maintenance", "Maintenance"), ("repair_history", "Repair history"),
        ("gate_pass", "Gate pass"), ("invoices", "Invoices"),
    ]),
    ("Directory", [
        ("departments", "Departments"), ("clients", "Clients"), ("technicians", "Technicians"),
    ]),
    ("System", [("reports", "Reports"), ("users_roles", "Users & roles"), ("settings", "Settings")]),
]


class Sidebar(QWidget):
    def __init__(self, app_name: str, role: str, on_navigate: Callable[[str], None], parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(232)
        self.role = role
        self._on_navigate = on_navigate
        self._buttons: dict[str, QPushButton] = {}
        self._active_key = "dashboard"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        brand = QWidget()
        brand_l = QVBoxLayout(brand)
        brand_l.setContentsMargins(22, 24, 22, 18)
        brand_l.setSpacing(3)
        name = QLabel(app_name.replace(" IT Console", ""))
        name.setObjectName("brandName")
        sub = QLabel("Asset & Maintenance Register")
        sub.setObjectName("brandSub")
        brand_l.addWidget(name)
        brand_l.addWidget(sub)
        outer.addWidget(brand)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        nav_host = QWidget()
        nav_l = QVBoxLayout(nav_host)
        nav_l.setContentsMargins(14, 6, 14, 10)
        nav_l.setSpacing(1)

        for group_label, items in NAV_GROUPS:
            visible_items = [
                (key, label) for key, label in items
                if permission_service.can_view_page(role, key)
            ]
            if not visible_items:
                continue  # spec section 31: hide unauthorized menu items — including empty groups
            gl = QLabel(group_label)
            gl.setProperty("class", "groupLabel")
            gl.setStyleSheet("QLabel { color: #A8A49B; font-size: 11px; font-weight: 600; padding-top: 10px; }")
            nav_l.addWidget(gl)
            for key, label in visible_items:
                btn = QPushButton(label.replace("&", "&&"))
                btn.setCursor(Qt.PointingHandCursor)
                btn.setProperty("navkey", key)
                btn.clicked.connect(lambda checked=False, k=key: self._select(k))
                self._buttons[key] = btn
                nav_l.addWidget(btn)

        nav_l.addStretch(1)
        scroll.setWidget(nav_host)
        outer.addWidget(scroll, 1)

        self._apply_styles()

    def _select(self, key: str):
        self._active_key = key
        self._apply_styles()
        self._on_navigate(key)

    def _apply_styles(self):
        for key, btn in self._buttons.items():
            if key == self._active_key:
                btn.setProperty("class", "navItemActive")
                btn.setStyleSheet(
                    "QPushButton { text-align:left; padding:8px 9px; border:none; "
                    "border-left:2px solid #3B3FA1; background:transparent; "
                    "color:#14171A; font-size:13px; font-weight:700; }"
                )
            else:
                btn.setProperty("class", "navItem")
                btn.setStyleSheet(
                    "QPushButton { text-align:left; padding:8px 10px; border:none; "
                    "border-left:2px solid transparent; background:transparent; "
                    "color:#4A4E54; font-size:13px; font-weight:500; }"
                    "QPushButton:hover { color:#14171A; }"
                )
