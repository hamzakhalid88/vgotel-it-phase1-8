from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QSplashScreen


def make_splash() -> QSplashScreen:
    pix = QPixmap(520, 320)
    pix.fill(QColor("#FFFFFF"))

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor("#E7E5E0"))
    p.drawRect(0, 0, pix.width() - 1, pix.height() - 1)

    p.setPen(QColor("#14171A"))
    title_font = QFont("Source Serif 4", 30, QFont.DemiBold)
    title_font.setItalic(True)
    p.setFont(title_font)
    p.drawText(pix.rect().adjusted(0, -30, 0, -30), Qt.AlignCenter, "Vgotel")

    p.setPen(QColor("#6B7178"))
    p.setFont(QFont("Inter", 11))
    p.drawText(pix.rect().adjusted(0, 30, 0, 30), Qt.AlignCenter, "IT Asset & Maintenance Console")

    p.setPen(QColor("#3B3FA1"))
    p.setFont(QFont("Inter", 9))
    p.drawText(pix.rect().adjusted(0, 120, 0, -20), Qt.AlignBottom | Qt.AlignHCenter, "Starting up…")
    p.end()

    return QSplashScreen(pix)
