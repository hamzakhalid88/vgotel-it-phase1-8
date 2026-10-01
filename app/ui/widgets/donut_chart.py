from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

DONUT_PALETTE = ["#3B3FA1", "#B7B9DE", "#A66A1D", "#E7E5E0", "#C9C5B8"]


class DonutChart(QWidget):
    def __init__(self, data: list[tuple[str, int]], center_label: str = "", parent=None):
        super().__init__(parent)
        self.data = data
        self.center_label = center_label
        self.setMinimumSize(128, 128)

    def set_data(self, data: list[tuple[str, int]], center_label: str = ""):
        self.data = data
        self.center_label = center_label
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height()) - 4
        rect = QRectF(2, 2, side, side)
        total = sum(v for _, v in self.data) or 1

        start_angle = 90 * 16  # start at 12 o'clock, Qt angles are in 1/16ths of a degree
        for i, (_, value) in enumerate(self.data):
            span = -int(round(360 * 16 * value / total))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(DONUT_PALETTE[i % len(DONUT_PALETTE)]))
            p.drawPie(rect, start_angle, span)
            start_angle += span

        # punch the hole
        hole_inset = side * 0.17
        hole_rect = QRectF(2 + hole_inset, 2 + hole_inset, side - 2 * hole_inset, side - 2 * hole_inset)
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(hole_rect)

        if self.center_label:
            num, _, unit = self.center_label.partition("\n")
            p.setPen(QColor("#14171A"))
            f = QFont("Source Serif 4", 15, QFont.DemiBold)
            p.setFont(f)
            p.drawText(hole_rect.adjusted(0, -8, 0, 0), Qt.AlignCenter, num)
            if unit:
                p.setPen(QColor("#6B7178"))
                p.setFont(QFont("Inter", 8))
                p.drawText(hole_rect.adjusted(0, 14, 0, 14), Qt.AlignCenter, unit)
