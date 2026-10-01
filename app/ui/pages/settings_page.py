"""
Phase 9 — Settings page (Administrator only).

Edits the non-secret fields in config/app_settings.json via save_config().
Changes to paths and backup policy take effect immediately for backup actions
and after restart for logging/attachment/export folders.
"""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame,
    QLineEdit, QSpinBox, QCheckBox, QPushButton, QMessageBox,
    QFileDialog, QLabel, QScrollArea,
)

from app.config import save_config
from app.services.backup_service import backup_database


class SettingsPage(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(20)

        # ---- Page title ----
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ---- General card ----
        general_card = self._make_card("General")
        gf = self._make_form()
        self.app_name_edit = QLineEdit(self.cfg.app_name)
        gf.addRow("Application name", self.app_name_edit)
        self.company_name_edit = QLineEdit(self.cfg.company_name)
        gf.addRow("Company name", self.company_name_edit)
        self.warranty_days = QSpinBox()
        self.warranty_days.setRange(1, 365)
        self.warranty_days.setValue(self.cfg.warranty_alert_days)
        gf.addRow("Warranty alert (days)", self.warranty_days)
        general_card.layout().addLayout(gf)
        root.addWidget(general_card)

        # ---- Paths card ----
        paths_card = self._make_card("Paths")
        pf = self._make_form()
        self.attachments_edit = self._path_row(pf, "Attachments folder", self.cfg.attachments_dir)
        self.exports_edit     = self._path_row(pf, "Exports folder",     self.cfg.exports_dir)
        self.backups_edit     = self._path_row(pf, "Backups folder",     self.cfg.backups_dir)
        self.logs_edit        = self._path_row(pf, "Logs folder",        self.cfg.logs_dir)
        paths_card.layout().addLayout(pf)
        root.addWidget(paths_card)

        # ---- Backup card ----
        backup_card = self._make_card("Backup")
        bc_layout = backup_card.layout()

        self.auto_backup = QCheckBox("Enable automatic backup on application exit")
        self.auto_backup.setChecked(self.cfg.auto_backup_enabled)
        bc_layout.addWidget(self.auto_backup)

        bf = self._make_form()
        self.backup_interval = QSpinBox()
        self.backup_interval.setRange(1, 168)
        self.backup_interval.setValue(self.cfg.auto_backup_interval_hours)
        bf.addRow("Auto-backup interval (hours)", self.backup_interval)

        self.keep_last_n = QSpinBox()
        self.keep_last_n.setRange(1, 100)
        self.keep_last_n.setValue(self.cfg.keep_last_n_backups)
        bf.addRow("Keep last N backups", self.keep_last_n)
        bc_layout.addLayout(bf)

        # Backup Now — left-aligned in its own row
        backup_btn_row = QHBoxLayout()
        backup_now_btn = QPushButton("Backup Now")
        backup_now_btn.setProperty("class", "btn")
        backup_now_btn.setCursor(Qt.PointingHandCursor)
        backup_now_btn.clicked.connect(self._on_backup_now)
        backup_btn_row.addWidget(backup_now_btn)
        backup_btn_row.addStretch()
        bc_layout.addLayout(backup_btn_row)

        root.addWidget(backup_card)

        # ---- Save row ----
        save_row = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.setProperty("class", "btnPrimary")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._on_save)
        save_row.addWidget(save_btn)
        save_row.addStretch()
        root.addLayout(save_row)

        root.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Small helpers for consistent Ledger styling
    # ------------------------------------------------------------------
    def _make_card(self, title_text: str) -> QFrame:
        """Return a card-styled QFrame (theme.py: QFrame.card) with a card title."""
        card = QFrame()
        card.setProperty("class", "card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(14)

        title = QLabel(title_text)
        title.setProperty("class", "cardTitle")   # theme.py: QLabel.cardTitle
        lay.addWidget(title)
        return card

    def _make_form(self) -> QFormLayout:
        """Return a QFormLayout tuned for Ledger-style left-aligned labels."""
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setHorizontalSpacing(24)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        return form

    def _path_row(self, form: QFormLayout, label: str, value: str) -> QLineEdit:
        row = QHBoxLayout()
        row.setSpacing(8)
        edit = QLineEdit(value)
        edit.setMinimumWidth(320)
        browse = QPushButton("Browse…")
        browse.setProperty("class", "btn")        # theme.py: QPushButton.btn
        browse.setCursor(Qt.PointingHandCursor)
        browse.setFixedWidth(96)
        browse.clicked.connect(lambda: self._browse(edit))
        row.addWidget(edit, 1)
        row.addWidget(browse)
        wrap = QWidget()
        wrap.setLayout(row)
        form.addRow(label, wrap)
        return edit

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _browse(self, edit: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, "Select folder", edit.text() or ".")
        if d:
            edit.setText(d)

    def _on_save(self):
        new_cfg = replace(
            self.cfg,
            app_name=self.app_name_edit.text().strip() or self.cfg.app_name,
            company_name=self.company_name_edit.text().strip() or self.cfg.company_name,
            warranty_alert_days=self.warranty_days.value(),
            attachments_dir=self.attachments_edit.text().strip(),
            exports_dir=self.exports_edit.text().strip(),
            backups_dir=self.backups_edit.text().strip(),
            logs_dir=self.logs_edit.text().strip(),
            auto_backup_enabled=self.auto_backup.isChecked(),
            auto_backup_interval_hours=self.backup_interval.value(),
            keep_last_n_backups=self.keep_last_n.value(),
        )
        save_config(new_cfg)
        self.cfg = new_cfg
        QMessageBox.information(
            self, "Settings",
            "Settings saved.\n\n"
            "Path changes take effect for new operations. "
            "Logging changes require an app restart."
        )

    def _on_backup_now(self):
        try:
            db_file = self.cfg.sqlite_file_path()
            if not db_file:
                QMessageBox.warning(
                    self, "Backup",
                    "Manual backup is only supported for the SQLite dialect.\n"
                    "For SQL Server, use SQL Server's own backup tools."
                )
                return
            path = backup_database(
                str(db_file),
                str(self.cfg.backups_path()),
                self.cfg.keep_last_n_backups,
            )
            QMessageBox.information(self, "Backup", f"Backup created:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Backup failed", str(e))