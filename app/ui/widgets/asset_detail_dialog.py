from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

STATUS_COLORS = {
    "Assigned": "#3B3FA1", "Available": "#2F6D4F", "Under Repair": "#A66A1D",
    "Inactive": "#6B7178", "Lost": "#A63D3D", "Retired": "#6B7178", "Scrapped": "#6B7178",
}


def _section(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setStyleSheet("QFrame{border:1px solid #E7E5E0; border-radius:6px;}")
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(20, 16, 20, 18)
    outer.setSpacing(10)
    t = QLabel(title)
    t.setStyleSheet("font-family:'Source Serif 4'; font-size:15px; font-weight:600; border:none;")
    outer.addWidget(t)
    return frame, outer


def _kv_row(label: str, value: str) -> QWidget:
    row = QWidget()
    l = QHBoxLayout(row)
    l.setContentsMargins(0, 0, 0, 0)
    lab = QLabel(label)
    lab.setStyleSheet("color:#6B7178; font-size:12px; border:none;")
    lab.setFixedWidth(140)
    val = QLabel(value)
    val.setStyleSheet("font-size:13px; font-weight:500; border:none;")
    val.setWordWrap(True)
    l.addWidget(lab)
    l.addWidget(val, 1)
    return row


class AssetDetailDialog(QDialog):
    def __init__(self, asset: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Asset {asset['asset_number']}")
        self.resize(720, 720)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        layout = QVBoxLayout(host)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)

        # ---- header -----------------------------------------------------
        head = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel(f"{asset['asset_number']} \u2014 {asset['asset_type']}")
        title.setStyleSheet("font-family:'Source Serif 4'; font-size:22px; font-weight:600;")
        sub = QLabel(f"Serial number: {asset['serial_number']}")
        sub.setStyleSheet("color:#6B7178; font-size:12.5px;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        head.addLayout(title_box, 1)

        badge = QLabel(asset["status"])
        color = STATUS_COLORS.get(asset["status"], "#6B7178")
        badge.setStyleSheet(
            f"color:{color}; border:1px solid {color}; border-radius:12px; "
            f"padding:5px 14px; font-size:12px; font-weight:600;"
        )
        head.addWidget(badge, 0, Qt.AlignTop)
        layout.addLayout(head)

        # ---- general + assignment ----------------------------------------
        gen_frame, gen_body = _section("General information")
        gen_body.addWidget(_kv_row("Asset type", asset["asset_type"]))
        gen_body.addWidget(_kv_row("Device", asset["device"]))
        gen_body.addWidget(_kv_row("Floor", asset["floor"]))
        layout.addWidget(gen_frame)

        assign_frame, assign_body = _section("Assignment")
        assign_body.addWidget(_kv_row("Department", asset["department"]))
        assign_body.addWidget(_kv_row("Assigned to", asset["client"]))
        layout.addWidget(assign_frame)

        # ---- purchase info -------------------------------------------------
        purchase_frame, purchase_body = _section("Purchase information")
        pd = asset["purchase_date"]
        purchase_body.addWidget(_kv_row("Purchase date", pd.strftime("%d %b %Y") if pd else "—"))
        purchase_body.addWidget(_kv_row("Vendor", asset["vendor"]))
        cost = asset.get("purchase_cost")
        purchase_body.addWidget(_kv_row("Cost", f"Rs {cost:,.0f}" if cost else "—"))
        layout.addWidget(purchase_frame)

        # ---- repair summary -------------------------------------------------
        summary_frame, summary_body = _section("Repair summary")
        row = QHBoxLayout()
        for label, value in [
            ("Total repairs", str(asset["repair_count"])),
            ("Total cost", f"Rs {asset['repair_total_cost']:,.0f}"),
            ("Average cost", f"Rs {asset['repair_avg_cost']:,.0f}"),
            ("Last repair", asset["last_repair_date"].strftime("%d %b %Y")
                if asset["last_repair_date"] else "—"),
        ]:
            cell = QVBoxLayout()
            v = QLabel(value)
            v.setStyleSheet("font-family:'Source Serif 4'; font-size:18px; font-weight:600; border:none;")
            l = QLabel(label)
            l.setStyleSheet("color:#6B7178; font-size:11px; border:none;")
            cell.addWidget(v)
            cell.addWidget(l)
            wrap = QWidget()
            wrap.setLayout(cell)
            row.addWidget(wrap)
        summary_body.addLayout(row)
        layout.addWidget(summary_frame)

        # ---- repair timeline -------------------------------------------------
        timeline_frame, timeline_body = _section("Repair timeline")
        timeline = asset.get("timeline") or []
        if not timeline:
            empty = QLabel("No repairs recorded for this asset yet.")
            empty.setStyleSheet("color:#6B7178; font-size:12.5px; border:none;")
            timeline_body.addWidget(empty)
        else:
            for i, h in enumerate(timeline):
                item = QFrame()
                if i < len(timeline) - 1:
                    item.setStyleSheet("border:none; border-bottom:1px solid #E7E5E0;")
                il = QVBoxLayout(item)
                il.setContentsMargins(0, 8, 0, 8)
                il.setSpacing(3)
                top_row = QHBoxLayout()
                date_lbl = QLabel(h["date"].strftime("%d %b %Y") if h["date"] else "—")
                date_lbl.setStyleSheet("font-weight:600; font-size:12.5px; border:none;")
                top_row.addWidget(date_lbl)
                cost_lbl = QLabel(f"Rs {h['cost']:,.0f}" if h["cost"] else "—")
                cost_lbl.setStyleSheet("color:#6B7178; font-size:12px; border:none;")
                top_row.addWidget(cost_lbl, 0, Qt.AlignRight)
                il.addLayout(top_row)
                issue_lbl = QLabel(f"{h['issue']} \u2014 {h['technician']}")
                issue_lbl.setStyleSheet("font-size:12.5px; border:none;")
                issue_lbl.setWordWrap(True)
                il.addWidget(issue_lbl)
                timeline_body.addWidget(item)
        layout.addWidget(timeline_frame)

        layout.addStretch(1)
