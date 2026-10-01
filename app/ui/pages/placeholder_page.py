from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    """Spec section 41 "empty states" applied honestly to modules that are
    scheduled but not yet built, instead of a broken/blank screen."""

    def __init__(self, title: str, phase_note: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 60, 40, 40)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(heading)

        note = QLabel(phase_note)
        note.setObjectName("pageSub")
        note.setAlignment(Qt.AlignCenter)
        note.setWordWrap(True)
        note.setMaximumWidth(420)
        layout.addSpacing(8)
        layout.addWidget(note)
