from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from app.db.base import session_scope
from app.db.models import User
from app.services import audit_service
from app.services.auth_service import authenticate


class LoginWindow(QWidget):
    def __init__(self, app_name: str, on_success: Callable[["User"], None], parent=None):
        super().__init__(parent)
        self._on_success = on_success
        self.setWindowTitle(app_name)
        self.resize(1000, 640)
        self.setStyleSheet("background:#FFFFFF;")

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setFixedWidth(360)
        card.setStyleSheet(
            "QFrame{background:#FCFCFB; border:1px solid #E7E5E0; border-radius:8px;}"
            "QLabel{background:transparent; border:none;}"
        )
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(36, 40, 36, 36)
        card_l.setSpacing(6)

        brand = QLabel("Vgotel")
        brand.setStyleSheet(
            "font-family:'Source Serif 4'; font-style:italic; font-size:28px; font-weight:600;"
        )
        brand.setAlignment(Qt.AlignCenter)
        card_l.addWidget(brand)

        sub = QLabel("IT Asset & Maintenance Console")
        sub.setStyleSheet("color:#6B7178; font-size:12.5px;")
        sub.setAlignment(Qt.AlignCenter)
        card_l.addWidget(sub)
        card_l.addSpacing(26)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.username.setStyleSheet(self._field_style())
        card_l.addWidget(self.username)
        card_l.addSpacing(10)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setStyleSheet(self._field_style())
        self.password.returnPressed.connect(self._try_login)
        card_l.addWidget(self.password)
        card_l.addSpacing(6)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color:#A63D3D; font-size:12px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        card_l.addWidget(self.error_label)
        card_l.addSpacing(12)

        login_btn = QPushButton("Sign in")
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet(
            "QPushButton{background:#14171A; color:white; padding:10px; "
            "border-radius:4px; font-size:13.5px; font-weight:600;}"
            "QPushButton:hover{background:#2A2E33;}"
        )
        login_btn.clicked.connect(self._try_login)
        card_l.addWidget(login_btn)
        card_l.addSpacing(18)

        demo_hint = QLabel("Local demo data — sign in as admin / Admin@123")
        demo_hint.setStyleSheet("color:#A8A49B; font-size:10.5px;")
        demo_hint.setAlignment(Qt.AlignCenter)
        demo_hint.setWordWrap(True)
        card_l.addWidget(demo_hint)

        outer.addWidget(card)

    @staticmethod
    def _field_style() -> str:
        return (
            "QLineEdit{border:1px solid #E7E5E0; border-radius:4px; padding:9px 10px; "
            "font-size:13.5px; background:white;}"
            "QLineEdit:focus{border-color:#3B3FA1;}"
        )

    def _try_login(self):
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self._show_error("Enter both a username and password.")
            return

        with session_scope() as s:
            user = authenticate(s, username, password)
            if user is None:
                audit_service.log_action(s, None, "Login Failed", "User", new_value=username)
                self._show_error("Incorrect username or password.")
                return
            audit_service.log_action(s, user.id, "Login", "User", record_id=user.id)
            full_name, role, uid = user.full_name, user.role, user.id

        self._on_success(uid, full_name, role)

    def _show_error(self, text: str):
        self.error_label.setText(text)
        self.error_label.show()
