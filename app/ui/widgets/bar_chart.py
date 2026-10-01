from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from app.ui.theme import COLORS


class BarChart(QWidget):
    def __init__(self, data: list[tuple[str, float]], value_fmt: str = "{:.0f}", parent=None):
        super().__init__(parent)
        self.data = data
        self.value_fmt = value_fmt
        self.setMinimumHeight(190)

    def set_data(self, data: list[tuple[str, float]]):
        self.data = data
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        if not self.data:
            return

        w, h = self.width(), self.height()
        top_pad, bottom_pad = 22, 34
        chart_h = h - top_pad - bottom_pad
        max_val = max((v for _, v in self.data), default=1) or 1

        n = len(self.data)
        gap = 16
        bar_w = min(34, (w - gap * (n + 1)) / n)
        total_w = bar_w * n + gap * (n + 1)
        x = (w - total_w) / 2 + gap

        label_font = QFont("Inter", 9)
        val_font = QFont("Inter", 8)
        val_font.setWeight(QFont.DemiBold)

        for i, (label, value) in enumerate(self.data):
            bar_h = (value / max_val) * chart_h if max_val else 0
            bar_top = top_pad + (chart_h - bar_h)
            is_last = i == n - 1
            color = QColor(COLORS["accent"]) if is_last else QColor("#D7D8EC")

            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawRect(QRectF(x, bar_top, bar_w, bar_h))

            p.setPen(QColor(COLORS["muted"]))
            p.setFont(val_font)
            p.drawText(
                QRectF(x - 10, bar_top - 16, bar_w + 20, 14),
                Qt.AlignCenter, self.value_fmt.format(value)
            )

            p.setFont(label_font)
            p.drawText(
                QRectF(x - 10, h - bottom_pad + 6, bar_w + 20, 16),
                Qt.AlignCenter, label
            )

            x += bar_w + gap
