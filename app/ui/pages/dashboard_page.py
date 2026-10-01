from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.db.base import session_scope
from app.services import dashboard_service
from app.ui.widgets.bar_chart import BarChart
from app.ui.widgets.donut_chart import DonutChart

STATUS_COLORS = {
    "Completed": "#2F6D4F", "Pending": "#A66A1D", "Received": "#A66A1D",
    "In Progress": "#3B3FA1", "In Repair": "#3B3FA1", "Overdue": "#A63D3D",
}


def _card(title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setProperty("class", "card")
    frame.setStyleSheet(
        "QFrame { background:#FFFFFF; border:1px solid #E7E5E0; border-radius:6px; }"
        "QLabel { background:transparent; border:none; }"
    )
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(20, 18, 20, 18)
    outer.setSpacing(4)

    t = QLabel(title)
    t.setStyleSheet("font-family:'Source Serif 4'; font-size:15px; font-weight:600; border:none;")
    outer.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setStyleSheet("color:#6B7178; font-size:11.5px; border:none;")
        outer.addWidget(s)
    outer.addSpacing(10)
    return frame, outer


class DashboardPage(QWidget):
    def __init__(self, warranty_alert_days: int, parent=None):
        super().__init__(parent)
        self.warranty_alert_days = warranty_alert_days

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        self.layout = QVBoxLayout(host)
        self.layout.setContentsMargins(40, 28, 40, 40)
        self.layout.setSpacing(20)

        self._build_header()
        self._alerts_frame = None
        self._kpi_frame = None
        self._build_placeholders()
        self.refresh()

    # ---- static chrome ---------------------------------------------------
    def _build_header(self):
        head = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        today_str = f"{dt.date.today().day} {dt.date.today().strftime('%B %Y')}"
        sub = QLabel(f"Here's what's happening across IT assets today, {today_str}.")
        sub.setObjectName("pageSub")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        head.addLayout(title_box, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("class", "btn")
        refresh_btn.setStyleSheet(
            "QPushButton{padding:7px 14px;border:1px solid #E7E5E0;border-radius:4px;"
            "background:#FFFFFF;font-size:13px;font-weight:500;}"
            "QPushButton:hover{border-color:#C7C3B8;}"
        )
        refresh_btn.clicked.connect(self.refresh)
        head.addWidget(refresh_btn)

        month_btn = QPushButton("This month")
        month_btn.setStyleSheet(
            "QPushButton{padding:7px 14px;border-radius:4px;background:#14171A;"
            "color:white;font-size:13px;font-weight:600;}"
        )
        head.addWidget(month_btn)
        self.layout.addLayout(head)

    def _build_placeholders(self):
        self._alerts_host = QWidget()
        self.layout.addWidget(self._alerts_host)
        self._kpi_host = QWidget()
        self.layout.addWidget(self._kpi_host)

        charts_row = QHBoxLayout()
        self.bar_card, bar_body = _card("Maintenance cost by month", "Last 6 months, PKR")
        self.bar_chart = BarChart([], value_fmt="{:,.0f}")
        bar_body.addWidget(self.bar_chart)
        charts_row.addWidget(self.bar_card, 7)

        self.donut_card, donut_body = _card("Asset status", "")
        donut_row = QHBoxLayout()
        self.donut_chart = DonutChart([])
        donut_row.addWidget(self.donut_chart)
        self.legend_box = QVBoxLayout()
        self.legend_box.setSpacing(9)
        legend_wrap = QWidget()
        legend_wrap.setLayout(self.legend_box)
        donut_row.addWidget(legend_wrap, 1)
        donut_body.addLayout(donut_row)
        charts_row.addWidget(self.donut_card, 5)
        self.layout.addLayout(charts_row)

        lower_row = QHBoxLayout()
        self.table_card, table_body = _card("Recent maintenance", "Latest updates across all departments")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Maintenance", "Device", "Department", "Technician", "Status", "Cost"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setStyleSheet(
            "QTableWidget{border:none;gridline-color:#F0EEE9;font-size:12.5px;}"
            "QHeaderView::section{background:white;border:none;border-bottom:1px solid #E7E5E0;"
            "color:#6B7178;font-size:11px;font-weight:600;padding:6px 4px;}"
        )
        table_body.addWidget(self.table)
        lower_row.addWidget(self.table_card, 8)

        side_col = QVBoxLayout()
        self.dept_card, dept_body = _card("Repairs by department", "Last 6 months")
        self.dept_rows_box = QVBoxLayout()
        self.dept_rows_box.setSpacing(10)
        dept_body.addLayout(self.dept_rows_box)
        side_col.addWidget(self.dept_card)

        self.warranty_card, warranty_body = _card(
            "Warranty expiring soon", f"Within {self.warranty_alert_days} days"
        )
        self.warranty_rows_box = QVBoxLayout()
        self.warranty_rows_box.setSpacing(8)
        warranty_body.addLayout(self.warranty_rows_box)
        side_col.addWidget(self.warranty_card)

        side_wrap = QWidget()
        side_wrap.setLayout(side_col)
        lower_row.addWidget(side_wrap, 4)
        self.layout.addLayout(lower_row)

    # ---- data-driven rebuilds ---------------------------------------------
    def refresh(self):
        with session_scope() as s:
            kpis = dashboard_service.get_kpis(s, self.warranty_alert_days)
            trend = dashboard_service.get_monthly_cost_trend(s)
            dist = dashboard_service.get_asset_status_distribution(s)
            by_dept = dashboard_service.get_repairs_by_department(s)
            warranty = dashboard_service.get_warranty_expiring(s, self.warranty_alert_days)
            recent = dashboard_service.get_recent_maintenance(s)

        self._rebuild_alerts(kpis, warranty_count=len(warranty))
        self._rebuild_kpis(kpis)
        self.bar_chart.set_data(trend)
        total_assets = kpis["total_assets"]
        self.donut_chart.set_data(dist, center_label=f"{total_assets:,}\nassets")
        self._rebuild_legend(dist)
        self._rebuild_dept_bars(by_dept)
        self._rebuild_warranty(warranty)
        self._rebuild_table(recent)

    def _rebuild_alerts(self, kpis, warranty_count: int):
        layout = QHBoxLayout()
        layout.setSpacing(0)
        items = [
            (f"<b>{kpis['overdue_repairs']} repairs</b> are overdue and need attention", "#A63D3D"),
            (f"<b>{warranty_count} assets\'</b> warranty expires soon", "#A66A1D"),
            (f"<b>{kpis['pending_repairs']} open</b> maintenance requests right now", "#3B3FA1"),
        ]
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame{border:1px solid #E7E5E0;border-radius:6px;}"
            "QLabel{background:transparent;border:none;}"
        )
        hl = QHBoxLayout(frame)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        for i, (text, color) in enumerate(items):
            cell = QFrame()
            if i < len(items) - 1:
                cell.setStyleSheet(
                    "QFrame{border:none;border-right:1px solid #E7E5E0;}"
                    "QLabel{background:transparent;border:none;}"
                )
            cell_l = QHBoxLayout(cell)
            cell_l.setContentsMargins(20, 13, 20, 13)
            sq = QLabel()
            sq.setFixedSize(6, 6)
            sq.setStyleSheet(f"background:{color}; border-radius:1px;")
            cell_l.addWidget(sq)
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size:13px; color:#4A4E54; border:none;")
            cell_l.addWidget(lbl, 1)
            hl.addWidget(cell, 1)

        old = self.layout.replaceWidget(self._alerts_host, frame)
        self._alerts_host.deleteLater()
        self._alerts_host = frame

    def _rebuild_kpis(self, kpis):
        grid_frame = QFrame()
        grid_frame.setStyleSheet(
            "QFrame{border-top:1px solid #E7E5E0; border-left:1px solid #E7E5E0;}"
            "QLabel{background:transparent;border:none;}"
        )
        grid = QGridLayout(grid_frame)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        cells = [
            ("Total assets", f"{kpis['total_assets']:,}", False),
            ("Assigned", f"{kpis['assigned']:,}", False),
            ("Available", f"{kpis['available']:,}", False),
            ("Under repair", f"{kpis['under_repair']:,}", False),
            ("Pending repairs", f"{kpis['pending_repairs']:,}", False),
            ("Overdue repairs", f"{kpis['overdue_repairs']:,}", True),
            ("Maintenance cost, this month", f"Rs {kpis['maintenance_cost_this_month']:,.0f}", False),
            ("Active technicians", f"{kpis['active_technicians']} / {kpis['total_technicians']}", False),
        ]
        for idx, (label, value, is_red) in enumerate(cells):
            row, col = divmod(idx, 4)
            cell = QFrame()
            cell.setStyleSheet(
                "QFrame{border:none;border-right:1px solid #E7E5E0;border-bottom:1px solid #E7E5E0;}"
                "QLabel{background:transparent;border:none;}"
            )
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(18, 16, 18, 16)
            cl.setSpacing(5)
            num = QLabel(value)
            color = "#A63D3D" if is_red else "#14171A"
            num.setStyleSheet(
                f"font-family:'Source Serif 4'; font-size:23px; font-weight:600; "
                f"color:{color}; border:none;"
            )
            lab = QLabel(label)
            lab.setStyleSheet("color:#6B7178; font-size:11px; border:none;")
            lab.setWordWrap(True)
            cl.addWidget(num)
            cl.addWidget(lab)
            grid.addWidget(cell, row, col)

        self.layout.replaceWidget(self._kpi_host, grid_frame)
        self._kpi_host.deleteLater()
        self._kpi_host = grid_frame

    def _rebuild_legend(self, dist):
        while self.legend_box.count():
            item = self.legend_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        palette = ["#3B3FA1", "#B7B9DE", "#A66A1D", "#E7E5E0", "#C9C5B8"]
        for i, (status, count) in enumerate(dist):
            row = QHBoxLayout()
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background:{palette[i % len(palette)]}; border-radius:1px;")
            row.addWidget(dot)
            lab = QLabel(status)
            lab.setStyleSheet("font-size:12.5px; color:#4A4E54;")
            row.addWidget(lab, 1)
            val = QLabel(f"{count:,}")
            val.setStyleSheet("font-size:12.5px; font-weight:600; color:#14171A;")
            row.addWidget(val)
            wrap = QWidget()
            wrap.setLayout(row)
            self.legend_box.addWidget(wrap)

    def _rebuild_dept_bars(self, by_dept):
        while self.dept_rows_box.count():
            item = self.dept_rows_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        max_val = max((v for _, v in by_dept), default=1) or 1
        for name, value in by_dept:
            row = QHBoxLayout()
            lab = QLabel(name)
            lab.setFixedWidth(110)
            lab.setStyleSheet("font-size:12px; color:#4A4E54;")
            row.addWidget(lab)

            bar = QProgressBar()
            bar.setRange(0, max_val)
            bar.setValue(value)
            bar.setTextVisible(False)
            bar.setFixedHeight(4)
            bar.setStyleSheet(
                "QProgressBar{background:#F1F0EC;border:none;border-radius:2px;}"
                "QProgressBar::chunk{background:#3B3FA1;border-radius:2px;}"
            )
            row.addWidget(bar, 1)

            val = QLabel(str(value))
            val.setFixedWidth(24)
            val.setAlignment(Qt.AlignRight)
            val.setStyleSheet("font-size:12px; color:#6B7178;")
            row.addWidget(val)

            wrap = QWidget()
            wrap.setLayout(row)
            self.dept_rows_box.addWidget(wrap)

    def _rebuild_warranty(self, warranty):
        self._last_warranty = warranty
        while self.warranty_rows_box.count():
            item = self.warranty_rows_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not warranty:
            empty = QLabel("No warranties expiring in this window.")
            empty.setStyleSheet("color:#6B7178; font-size:12px;")
            self.warranty_rows_box.addWidget(empty)
            return
        for w in warranty:
            row = QHBoxLayout()
            text_box = QVBoxLayout()
            name = QLabel(w["device"])
            name.setStyleSheet("font-size:13px; font-weight:500;")
            sub = QLabel(f"{w['department']} · {w['asset_number']}")
            sub.setStyleSheet("font-size:11px; color:#6B7178;")
            text_box.addWidget(name)
            text_box.addWidget(sub)
            row.addLayout(text_box, 1)
            days = QLabel(f"{w['days_left']}d")
            days.setStyleSheet("font-size:12px; font-weight:600; color:#A66A1D;")
            row.addWidget(days, 0, Qt.AlignTop)
            wrap = QWidget()
            wrap.setLayout(row)
            wrap.setStyleSheet("border-bottom:1px solid #E7E5E0;")
            self.warranty_rows_box.addWidget(wrap)

    def _rebuild_table(self, recent):
        self.table.setRowCount(len(recent))
        for r, m in enumerate(recent):
            values = [
                m["maintenance_number"], m["device"], m["department"],
                m["technician"], m["status"],
                f"Rs {m['cost']:,.0f}" if m["cost"] else "—",
            ]
            for c, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if c == 0:
                    item.setForeground(Qt.GlobalColor.darkBlue)
                if c == 4:
                    from PySide6.QtGui import QColor
                    item.setForeground(QColor(STATUS_COLORS.get(val, "#14171A")))
                self.table.setItem(r, c, item)
