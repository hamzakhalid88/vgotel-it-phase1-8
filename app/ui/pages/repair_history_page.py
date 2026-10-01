from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.db.base import session_scope
from app.services import repair_history_service as rsvc


class RepairHistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 28, 40, 40)
        outer.setSpacing(16)

        title = QLabel("Repair history")
        title.setObjectName("pageTitle")
        sub = QLabel("Every completed repair, across every asset, calculated automatically.")
        sub.setObjectName("pageSub")
        outer.addWidget(title)
        outer.addWidget(sub)

        self.stat_row = QHBoxLayout()
        outer.addLayout(self.stat_row)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by asset number or issue\u2026")
        self.search_box.setMaximumWidth(320)
        self.search_box.setStyleSheet(
            "QLineEdit{padding:7px 10px; border:1px solid #E7E5E0; border-radius:4px; font-size:13px;}"
        )
        self.search_box.textChanged.connect(self.refresh)
        outer.addWidget(self.search_box)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Asset", "Repair date", "Issue", "Technician", "Status", "Cost"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setStyleSheet(
            "QTableWidget{border:1px solid #E7E5E0; border-radius:6px; gridline-color:#F0EEE9; font-size:13px;}"
            "QHeaderView::section{background:#FCFCFB; border:none; border-bottom:1px solid #E7E5E0;"
            "color:#6B7178; font-size:11px; font-weight:600; padding:8px;}"
        )
        outer.addWidget(self.table, 1)

        self.refresh()

    def _stat_cell(self, label: str, value: str) -> QWidget:
        frame = QWidget()
        frame.setStyleSheet("QWidget{border:1px solid #E7E5E0; border-radius:6px;}")
        l = QVBoxLayout(frame)
        l.setContentsMargins(18, 14, 18, 14)
        v = QLabel(value)
        v.setStyleSheet("font-family:'Source Serif 4'; font-size:21px; font-weight:600; border:none;")
        lab = QLabel(label)
        lab.setStyleSheet("color:#6B7178; font-size:11.5px; border:none;")
        l.addWidget(v)
        l.addWidget(lab)
        return frame

    def refresh(self):
        with session_scope() as s:
            rows = rsvc.list_repair_history(s, self.search_box.text().strip())
        stats = rsvc.summary(rows)

        while self.stat_row.count():
            item = self.stat_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.stat_row.addWidget(self._stat_cell("Total repairs", f"{stats['total_repairs']:,}"))
        self.stat_row.addWidget(self._stat_cell("Total cost", f"Rs {stats['total_cost']:,.0f}"))
        self.stat_row.addWidget(self._stat_cell("Average cost", f"Rs {stats['avg_cost']:,.0f}"))

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [
                row["asset_number"],
                row["repair_date"].strftime("%d %b %Y") if row["repair_date"] else "\u2014",
                row["issue"], row["technician"], row["status"],
                f"Rs {row['cost']:,.0f}" if row["cost"] else "\u2014",
            ]
            for c, val in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))
