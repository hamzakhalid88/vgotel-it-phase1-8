from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

from app.db.base import session_scope
from app.services import attachment_service, audit_service, permission_service
from app.services import invoice_service as isvc
from app.services import maintenance_service as msvc

WARRANTY_COLORS = {"Active": "#2F6D4F", "Expiring soon": "#A66A1D", "Expired": "#A63D3D"}

STATUS_COLORS = {
    "Received": "#6B7178", "Assigned": "#3B3FA1", "In Repair": "#A66A1D",
    "Completed": "#2F6D4F", "Returned": "#2F6D4F", "Closed": "#6B7178", "Overdue": "#A63D3D",
}


def _kv(label: str, value: str) -> QWidget:
    row = QWidget()
    l = QHBoxLayout(row)
    l.setContentsMargins(0, 4, 0, 4)
    lab = QLabel(label)
    lab.setFixedWidth(150)
    lab.setStyleSheet("color:#6B7178; font-size:12px;")
    val = QLabel(value)
    val.setStyleSheet("font-size:13px; font-weight:500;")
    val.setWordWrap(True)
    l.addWidget(lab)
    l.addWidget(val, 1)
    return row


def _tab(rows: list[QWidget]) -> QWidget:
    w = QWidget()
    l = QVBoxLayout(w)
    l.setContentsMargins(18, 16, 18, 16)
    l.setSpacing(2)
    for r in rows:
        l.addWidget(r)
    l.addStretch(1)
    return w


class MaintenanceDetailDialog(QDialog):
    def __init__(self, maintenance_id: int, current_user_id: int, role: str, parent=None):
        super().__init__(parent)
        self.maintenance_id = maintenance_id
        self.current_user_id = current_user_id
        self.role = role
        self.can_write_maintenance = permission_service.can_write(role, "maintenance")
        self.can_write_invoices = permission_service.can_write(role, "invoices")
        self.changed = False
        self.resize(760, 640)

        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(24, 22, 24, 20)
        self._build()

    def _load(self) -> dict:
        with session_scope() as s:
            return msvc.get_maintenance_detail(s, self.maintenance_id)

    def _clear(self):
        while self.outer.count():
            item = self.outer.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _build(self):
        self._clear()
        m = self._load()
        self.setWindowTitle(f"Maintenance {m['maintenance_number']}")

        head = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel(f"Maintenance {m['maintenance_number']}")
        title.setStyleSheet("font-family:'Source Serif 4'; font-size:20px; font-weight:600;")
        sub = QLabel(f"{m['device']} \u2014 {m['asset_number']}")
        sub.setStyleSheet("color:#6B7178; font-size:12.5px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        head.addLayout(title_box, 1)

        color = STATUS_COLORS.get(m["display_status"], "#6B7178")
        badge = QLabel(m["display_status"])
        badge.setStyleSheet(
            f"color:{color}; border:1px solid {color}; border-radius:12px; "
            f"padding:5px 14px; font-size:12px; font-weight:600;"
        )
        head.addWidget(badge, 0, Qt.AlignTop)
        self.outer.addLayout(head)
        self.outer.addSpacing(10)

        tabs = QTabWidget()
        tabs.addTab(_tab([
            _kv("Department", m["department"]), _kv("Employee", m["employee_name"]),
            _kv("Device", m["device"]), _kv("Technician", m["technician"]),
            _kv("Cost", f"Rs {m['cost']:,.0f}" if m["cost"] else "\u2014"),
            _kv("Gate pass", m["gate_pass_number"]), _kv("Invoice", m["invoice_number"]),
            _kv("Entry date", m["entry_date"].strftime("%d %b %Y") if m["entry_date"] else "\u2014"),
            _kv("Expected return", m["expected_return_date"].strftime("%d %b %Y")
                if m["expected_return_date"] else "\u2014"),
        ]), "Overview")

        tabs.addTab(_tab([_kv("Issue", m["issue"]), _kv("Notes", m["notes"])]), "Problem")

        tabs.addTab(_tab([
            _kv("Repair details", m["repair_details"]),
            _kv("Completed date", m["completed_date"].strftime("%d %b %Y")
                if m["completed_date"] else "\u2014"),
        ]), "Repair details")

        tabs.addTab(_tab([
            _kv("Technician", m["technician"]), _kv("Shop", m["technician_shop"]),
            _kv("Shop contact", m["technician_contact"]),
            _kv("Gate pass reason", m["gate_pass_reason"]),
            _kv("Authorized by", m["authorized_by"]),
            _kv("Actual return", m["actual_return_date"].strftime("%d %b %Y")
                if m["actual_return_date"] else "\u2014"),
        ]), "Technician")

        w_status = isvc.warranty_status(m["warranty_until"])
        warranty_rows = [
            _kv("Warranty months", str(m["warranty_months"]) if m["warranty_months"] else "\u2014"),
            _kv("Warranty until", m["warranty_until"].strftime("%d %b %Y")
                if m["warranty_until"] else "\u2014"),
        ]
        if w_status != "\u2014":
            wcolor = WARRANTY_COLORS.get(w_status, "#6B7178")
            wbadge = QLabel(w_status)
            wbadge.setStyleSheet(
                f"color:{wcolor}; border:1px solid {wcolor}; border-radius:11px; "
                f"padding:4px 12px; font-size:11.5px; font-weight:600;"
            )
            wrow = QHBoxLayout()
            wlab = QLabel("Status")
            wlab.setFixedWidth(150)
            wlab.setStyleSheet("color:#6B7178; font-size:12px;")
            wrow.addWidget(wlab)
            wrow.addWidget(wbadge, 0, Qt.AlignLeft)
            wrow.addStretch(1)
            wwrap = QWidget()
            wwrap.setLayout(wrow)
            warranty_rows.insert(0, wwrap)
        tabs.addTab(_tab(warranty_rows), "Warranty")

        tabs.addTab(_tab([
            _kv("Repair cost", f"Rs {m['cost']:,.0f}" if m["cost"] else "\u2014"),
            _kv("Invoice number", m["invoice_number"]),
        ]), "Financial")

        tabs.addTab(self._attachments_tab(m), "Attachments")

        history_rows = self._history_rows()
        tabs.addTab(_tab(history_rows), "History")

        self.outer.addWidget(tabs, 1)

        self.outer.addSpacing(12)
        actions = QHBoxLayout()
        actions.addStretch(1)
        for label, handler in self._available_actions(m):
            btn = QPushButton(label)
            btn.setStyleSheet(
                "QPushButton{padding:8px 16px; border-radius:4px; background:#14171A; color:white;"
                "font-size:13px; font-weight:600;} QPushButton:hover{background:#2A2E33;}"
            )
            btn.clicked.connect(handler)
            actions.addWidget(btn)
        self.outer.addLayout(actions)

    def _history_rows(self) -> list[QWidget]:
        from app.db.models import AuditLog
        from sqlalchemy import select
        with session_scope() as s:
            logs = s.scalars(
                select(AuditLog).where(
                    AuditLog.entity == "Maintenance", AuditLog.record_id == self.maintenance_id
                ).order_by(AuditLog.timestamp.asc())
            ).all()
            rows = []
            for log in logs:
                old_v = log.old_value or "\u2014"
                new_v = log.new_value or "\u2014"
                rows.append(_kv(
                    log.timestamp.strftime("%d %b %Y %H:%M"),
                    f"{log.action}: {old_v} \u2192 {new_v}",
                ))
        return rows or [QLabel("No history recorded yet.")]

    def _attachments_tab(self, m: dict) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(18, 16, 18, 16)
        l.setSpacing(10)

        bill_image = m.get("bill_image")
        if bill_image:
            full_path = attachment_service.resolve(bill_image)
            pix = QPixmap(str(full_path))
            if not pix.isNull():
                preview = QLabel()
                preview.setPixmap(pix.scaledToWidth(280, Qt.SmoothTransformation))
                preview.setStyleSheet("border:1px solid #E7E5E0; border-radius:4px;")
                l.addWidget(preview, 0, Qt.AlignLeft)
            name_lbl = QLabel(full_path.name)
            name_lbl.setStyleSheet("font-size:12.5px; color:#4A4E54;")
            l.addWidget(name_lbl)

            btn_row = QHBoxLayout()
            open_btn = QPushButton("Open")
            open_btn.setStyleSheet(self._link_style("#3B3FA1"))
            open_btn.clicked.connect(lambda: self._open_attachment(full_path))
            btn_row.addWidget(open_btn)
            if self.can_write_maintenance:
                remove_btn = QPushButton("Remove")
                remove_btn.setStyleSheet(self._link_style("#A63D3D"))
                remove_btn.clicked.connect(self._act_remove_attachment)
                btn_row.addWidget(remove_btn)
            btn_row.addStretch(1)
            l.addLayout(btn_row)
        else:
            empty = QLabel("No bill image attached yet.")
            empty.setStyleSheet("color:#6B7178; font-size:12.5px;")
            l.addWidget(empty)
            if self.can_write_maintenance:
                upload_btn = QPushButton("Upload bill image")
                upload_btn.setStyleSheet(
                    "QPushButton{padding:7px 14px; border:1px solid #E7E5E0; border-radius:4px; "
                    "font-size:12.5px; font-weight:600;} QPushButton:hover{border-color:#C7C3B8;}"
                )
                upload_btn.clicked.connect(self._act_upload_attachment)
                l.addWidget(upload_btn, 0, Qt.AlignLeft)

        l.addStretch(1)
        return w

    @staticmethod
    def _link_style(color: str) -> str:
        return (
            f"QPushButton{{border:none; background:transparent; color:{color}; "
            f"font-size:12px; font-weight:600;}} QPushButton:hover{{text-decoration:underline;}}"
        )

    def _open_attachment(self, path):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _act_upload_attachment(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select bill image", "", "Images (*.png *.jpg *.jpeg *.pdf)"
        )
        if not file_path:
            return
        m = self._load()
        try:
            rel_path = attachment_service.store_bill_image(
                file_path, m["maintenance_number"], m["entry_date"]
            )
        except FileNotFoundError as e:
            QMessageBox.warning(self, "Couldn't attach that file", str(e))
            return
        with session_scope() as s:
            msvc.set_bill_image(s, self.role, self.maintenance_id, rel_path)
            audit_service.log_action(s, self.current_user_id, "Update", "Maintenance",
                                      self.maintenance_id, None, "Bill image attached")
        self._refresh_after_change("attachment added")

    def _act_remove_attachment(self):
        confirm = QMessageBox.question(
            self, "Remove attachment?", "Remove this bill image? This can't be undone."
        )
        if confirm != QMessageBox.Yes:
            return
        with session_scope() as s:
            old_path = msvc.clear_bill_image(s, self.role, self.maintenance_id)
            audit_service.log_action(s, self.current_user_id, "Delete", "Maintenance",
                                      self.maintenance_id, "Bill image", None)
        if old_path:
            try:
                attachment_service.remove_bill_image(old_path)
            except OSError:
                pass  # DB reference is already cleared; a stray file isn't worth failing over
        self._refresh_after_change("attachment removed")

    def _available_actions(self, m: dict):
        status = m["status"]
        actions = []
        if not self.can_write_maintenance and not self.can_write_invoices:
            return actions
        if self.can_write_maintenance:
            if status == "Received":
                return [("Assign technician", self._act_assign)]
            if status == "Assigned":
                return [("Start repair", self._act_start_repair)]
            if status == "In Repair":
                return [("Mark completed", self._act_complete)]
            if status == "Completed":
                actions.append(("Mark returned", self._act_return))
            if status == "Returned":
                actions.append(("Close case", self._act_close))
        if self.can_write_invoices and status in ("Completed", "Returned", "Closed") \
                and m["invoice_number"] == "\u2014":
            actions.append(("Generate invoice", self._act_generate_invoice))
        return actions

    def _act_generate_invoice(self):
        from app.config import load_config
        cfg = load_config()
        with session_scope() as s:
            number = isvc.generate_invoice(s, self.role, self.maintenance_id, cfg.invoice_prefix)
            audit_service.log_action(s, self.current_user_id, "Create", "Invoice",
                                      self.maintenance_id, None, number)
        self._refresh_after_change("invoice generated")

    def _refresh_after_change(self, note: str):
        self.changed = True
        self._build()

    def _act_assign(self):
        from sqlalchemy import select
        from app.db.models import Technician
        from app.ui.widgets.form_dialog import FieldSpec, FormDialog
        with session_scope() as s:
            techs = [(t.id, t.name) for t in s.scalars(
                select(Technician).where(Technician.is_active.is_(True)).order_by(Technician.name)
            ).all()]
        dlg = FormDialog("Assign technician", [
            FieldSpec("technician_id", "Technician", kind="combo", choices=techs, required=True)
        ], parent=self)
        if dlg.exec() != FormDialog.Accepted:
            return
        with session_scope() as s:
            msvc.assign_technician(s, self.role, self.maintenance_id, dlg.values["technician_id"])
            audit_service.log_action(s, self.current_user_id, "StatusChange", "Maintenance",
                                      self.maintenance_id, "Received", "Assigned")
        self._refresh_after_change("assigned")

    def _act_start_repair(self):
        confirm = QMessageBox.question(self, "Start repair?", "Mark this case as In Repair?")
        if confirm != QMessageBox.Yes:
            return
        with session_scope() as s:
            msvc.start_repair(s, self.role, self.maintenance_id)
            audit_service.log_action(s, self.current_user_id, "StatusChange", "Maintenance",
                                      self.maintenance_id, "Assigned", "In Repair")
        self._refresh_after_change("started")

    def _act_complete(self):
        from app.ui.widgets.form_dialog import FieldSpec, FormDialog
        dlg = FormDialog("Mark completed", [
            FieldSpec("repair_details", "Repair details", kind="multiline", required=True),
            FieldSpec("cost", "Cost (Rs)", kind="number", min_value=0, required=True),
            FieldSpec("completed_date", "Completed date", kind="date"),
            FieldSpec("warranty_months", "Warranty (months)", kind="number", min_value=0),
        ], parent=self)
        if dlg.exec() != FormDialog.Accepted:
            return
        v = dlg.values
        try:
            with session_scope() as s:
                msvc.complete_repair(
                    s, self.role, self.maintenance_id, v["repair_details"], v["cost"],
                    v["completed_date"], int(v["warranty_months"] or 0),
                )
                audit_service.log_action(s, self.current_user_id, "StatusChange", "Maintenance",
                                          self.maintenance_id, "In Repair", "Completed")
        except msvc.ValidationError as e:
            QMessageBox.warning(self, "Can't save that", str(e))
            return
        self._refresh_after_change("completed")

    def _act_return(self):
        from app.ui.widgets.form_dialog import FieldSpec, FormDialog
        dlg = FormDialog("Mark returned", [
            FieldSpec("actual_return_date", "Actual return date", kind="date"),
        ], parent=self)
        if dlg.exec() != FormDialog.Accepted:
            return
        with session_scope() as s:
            msvc.return_device(s, self.role, self.maintenance_id, dlg.values["actual_return_date"])
            audit_service.log_action(s, self.current_user_id, "StatusChange", "Maintenance",
                                      self.maintenance_id, "Completed", "Returned")
        self._refresh_after_change("returned")

    def _act_close(self):
        confirm = QMessageBox.question(
            self, "Close this maintenance case?",
            "Are you sure you want to close this maintenance case? This is its final state.",
        )
        if confirm != QMessageBox.Yes:
            return
        with session_scope() as s:
            msvc.close_case(s, self.role, self.maintenance_id)
            audit_service.log_action(s, self.current_user_id, "StatusChange", "Maintenance",
                                      self.maintenance_id, "Returned", "Closed")
        self._refresh_after_change("closed")
