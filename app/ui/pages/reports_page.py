from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDateEdit, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QMessageBox, QPushButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.db.base import session_scope
from app.services import export_service as esvc
from app.services import report_service as rsvc

NEEDS_DATE_RANGE = {"maintenance_report", "department_cost"}


class ReportViewerDialog(QDialog):
    def __init__(self, report_key: str, title: str, runner, generated_by: str,
                 can_export: bool = True, parent=None):
        super().__init__(parent)
        self.report_key = report_key
        self.runner = runner
        self.generated_by = generated_by
        self.can_export = can_export
        self.setWindowTitle(title)
        self.resize(920, 640)

        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(24, 22, 24, 20)

        head = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel(title)
        t.setStyleSheet("font-family:'Source Serif 4'; font-size:20px; font-weight:600;")
        sub = QLabel(f"Generated {dt.datetime.now().strftime('%d %b %Y %H:%M')} by {generated_by}")
        sub.setStyleSheet("color:#6B7178; font-size:12px;")
        title_box.addWidget(t)
        title_box.addWidget(sub)
        head.addLayout(title_box, 1)
        self.outer.addLayout(head)
        self.outer.addSpacing(8)

        self.date_from = None
        self.date_to = None
        if report_key in NEEDS_DATE_RANGE:
            filt_row = QHBoxLayout()
            filt_row.addWidget(QLabel("From"))
            self.date_from = QDateEdit()
            self.date_from.setCalendarPopup(True)
            self.date_from.setDate(self.date_from.date().addMonths(-6))
            filt_row.addWidget(self.date_from)
            filt_row.addWidget(QLabel("To"))
            self.date_to = QDateEdit()
            self.date_to.setCalendarPopup(True)
            filt_row.addWidget(self.date_to)
            apply_btn = QPushButton("Apply")
            apply_btn.setStyleSheet(
                "QPushButton{padding:6px 14px; border:1px solid #E7E5E0; border-radius:4px; font-size:12.5px;}"
            )
            apply_btn.clicked.connect(self._reload)
            filt_row.addWidget(apply_btn)
            filt_row.addStretch(1)
            self.outer.addLayout(filt_row)
            self.outer.addSpacing(8)

        self.summary_row = QHBoxLayout()
        self.outer.addLayout(self.summary_row)

        self.table = QTableWidget(0, 0)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet(
            "QTableWidget{border:1px solid #E7E5E0; border-radius:6px; gridline-color:#F0EEE9; font-size:12.5px;}"
            "QHeaderView::section{background:#FCFCFB; border:none; border-bottom:1px solid #E7E5E0;"
            "color:#6B7178; font-size:11px; font-weight:600; padding:7px;}"
        )
        self.outer.addWidget(self.table, 1)

        export_row = QHBoxLayout()
        export_row.addStretch(1)
        if self.can_export:
            for label, fmt in [("Export CSV", "csv"), ("Export Excel", "xlsx"), ("Export PDF", "pdf")]:
                btn = QPushButton(label)
                btn.setStyleSheet(
                    "QPushButton{padding:8px 16px; border-radius:4px; background:#14171A; color:white;"
                    "font-size:13px; font-weight:600;} QPushButton:hover{background:#2A2E33;}"
                )
                btn.clicked.connect(lambda checked=False, f=fmt: self._export(f))
                export_row.addWidget(btn)
        else:
            note = QLabel("Your role can view this report but not export it.")
            note.setStyleSheet("color:#6B7178; font-size:12px;")
            export_row.addWidget(note)
        self.outer.addLayout(export_row)

        self._current_report = None
        self._reload()

    def _get_filters(self) -> dict:
        if self.date_from and self.date_to:
            return {
                "date_from": self.date_from.date().toPython(),
                "date_to": self.date_to.date().toPython(),
            }
        return {}

    def _reload(self):
        with session_scope() as s:
            report = self.runner(s, self._get_filters())
        self._current_report = report
        self._render(report)

    def _render(self, report: dict):
        while self.summary_row.count():
            item = self.summary_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if report.get("summary"):
            for label, value in report["summary"]:
                cell = QFrame()
                cell.setStyleSheet("QFrame{border:1px solid #E7E5E0; border-radius:6px;}")
                cl = QVBoxLayout(cell)
                cl.setContentsMargins(14, 10, 14, 10)
                v = QLabel(str(value))
                v.setStyleSheet("font-family:'Source Serif 4'; font-size:17px; font-weight:600; border:none;")
                lab = QLabel(label)
                lab.setStyleSheet("color:#6B7178; font-size:10.5px; border:none;")
                cl.addWidget(v)
                cl.addWidget(lab)
                self.summary_row.addWidget(cell)
            self.summary_row.addStretch(1)

        cols = report["columns"]
        rows = report["rows"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))
        if cols:
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        if not rows:
            self.table.setRowCount(1)
            empty_item = QTableWidgetItem("No data for this report yet.")
            self.table.setItem(0, 0, empty_item)
            self.table.setSpan(0, 0, 1, max(len(cols), 1))

    def _export(self, fmt: str):
        if not self._current_report:
            return
        suggested = esvc.default_export_path(self.report_key, fmt)
        filters = {"csv": "CSV files (*.csv)", "xlsx": "Excel files (*.xlsx)", "pdf": "PDF files (*.pdf)"}
        path, _ = QFileDialog.getSaveFileName(self, "Export report", suggested, filters[fmt])
        if not path:
            return
        try:
            if fmt == "csv":
                esvc.export_csv(path, self.windowTitle(), self._current_report)
            elif fmt == "xlsx":
                esvc.export_excel(path, self.windowTitle(), self._current_report, self.generated_by)
            else:
                esvc.export_pdf(path, self.windowTitle(), self._current_report, self.generated_by)
        except Exception as e:
            QMessageBox.warning(self, "Export failed", f"Couldn't export this report: {e}")
            return
        QMessageBox.information(self, "Exported", f"Saved to {path}")


class ReportsHubPage(QWidget):
    def __init__(self, generated_by: str, can_export: bool = True, parent=None):
        super().__init__(parent)
        self.generated_by = generated_by
        self.can_export = can_export

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(40, 28, 40, 40)
        layout.setSpacing(22)

        title = QLabel("Reports")
        title.setObjectName("pageTitle")
        sub = QLabel("Asset, maintenance, financial and warranty reports \u2014 export to CSV, Excel or PDF.")
        sub.setObjectName("pageSub")
        layout.addWidget(title)
        layout.addWidget(sub)

        for category, reports in rsvc.REPORTS.items():
            cat_label = QLabel(category)
            cat_label.setStyleSheet(
                "font-family:'Source Serif 4'; font-size:16px; font-weight:600; margin-top:6px;"
            )
            layout.addWidget(cat_label)

            grid = QGridLayout()
            grid.setSpacing(12)
            for i, (key, label, runner) in enumerate(reports):
                card = self._report_card(key, label, runner)
                grid.addWidget(card, i // 3, i % 3)
            layout.addLayout(grid)

        layout.addStretch(1)

    def _report_card(self, key: str, label: str, runner) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:#FFFFFF; border:1px solid #E7E5E0; border-radius:6px;}"
            "QFrame:hover{border-color:#3B3FA1;}"
        )
        card.setCursor(Qt.PointingHandCursor)
        l = QVBoxLayout(card)
        l.setContentsMargins(16, 14, 16, 14)
        lab = QLabel(label)
        lab.setStyleSheet("font-size:13px; font-weight:600; border:none;")
        lab.setWordWrap(True)
        hint = QLabel("View \u2192")
        hint.setStyleSheet("color:#3B3FA1; font-size:11.5px; border:none;")
        l.addWidget(lab)
        l.addWidget(hint)
        card.mousePressEvent = lambda event, k=key, lb=label, r=runner: self._open(k, lb, r)
        return card

    def _open(self, key: str, label: str, runner):
        ReportViewerDialog(key, label, runner, self.generated_by,
                            can_export=self.can_export, parent=self).exec()
