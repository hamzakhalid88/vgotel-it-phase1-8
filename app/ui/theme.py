"""
The "Ledger" design language — same tokens as the approved HTML preview
(design-3-ledger-minimal.html): paper-like, serif headings for structure,
Inter for UI/data, a single indigo accent, thin warm-neutral rules instead
of card shadows.

Fonts are referenced by family name with a plain-sans / serif fallback
chain rather than bundled — Qt will use "Inter" / "Source Serif 4" if
they're installed on the machine and fall back gracefully if not. See
README.md "Fonts" for the one-line install recommendation.
"""
from __future__ import annotations

COLORS = {
    "bg": "#FFFFFF",
    "surface": "#FCFCFB",
    "ink": "#14171A",
    "muted": "#6B7178",
    "accent": "#3B3FA1",
    "accent_tint": "#ECEDF7",
    "border": "#E7E5E0",
    "green": "#2F6D4F",
    "green_bg": "#EAF2ED",
    "ochre": "#A66A1D",
    "ochre_bg": "#F7EEE0",
    "brick": "#A63D3D",
    "brick_bg": "#F7EAEA",
}

SANS = "Inter, 'Segoe UI', Arial, sans-serif"
SERIF = "'Source Serif 4', Georgia, 'Times New Roman', serif"

QSS = f"""
* {{
    font-family: {SANS};
    color: {COLORS['ink']};
    outline: none;
}}
QWidget {{
    background: {COLORS['bg']};
    border: none;
}}
QLabel {{
    border: none;
    background: transparent;
}}
QWidget#sidebar {{
    background: {COLORS['surface']};
    border-right: 1px solid {COLORS['border']};
}}
QLabel#brandName {{
    font-family: {SERIF};
    font-style: italic;
    font-size: 20px;
    font-weight: 600;
}}
QLabel#brandSub, QLabel.muted {{
    color: {COLORS['muted']};
    font-size: 11px;
}}
QLabel.groupLabel {{
    color: #A8A49B;
    font-size: 11px;
    font-weight: 600;
    padding-top: 10px;
}}
QPushButton.navItem {{
    text-align: left;
    padding: 8px 10px;
    border: none;
    border-left: 2px solid transparent;
    background: transparent;
    color: #4A4E54;
    font-size: 13px;
    font-weight: 500;
    border-radius: 0px;
}}
QPushButton.navItem:hover {{
    color: {COLORS['ink']};
}}
QPushButton.navItemActive {{
    text-align: left;
    padding: 8px 9px;
    border: none;
    border-left: 2px solid {COLORS['accent']};
    background: transparent;
    color: {COLORS['ink']};
    font-size: 13px;
    font-weight: 700;
}}
QWidget#topbar {{
    background: {COLORS['bg']};
    border-bottom: 1px solid {COLORS['border']};
}}
QLineEdit#searchBox {{
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    padding: 6px 2px;
    font-size: 13px;
    background: transparent;
}}
QLabel#pageTitle {{
    font-family: {SERIF};
    font-size: 26px;
    font-weight: 600;
}}
QLabel#pageSub {{
    color: {COLORS['muted']};
    font-size: 13px;
}}
QPushButton.btn {{
    padding: 7px 14px;
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background: {COLORS['bg']};
    font-size: 13px;
    font-weight: 500;
}}
QPushButton.btn:hover {{
    border-color: #C7C3B8;
}}
QPushButton.btnPrimary {{
    padding: 7px 14px;
    border-radius: 4px;
    background: {COLORS['ink']};
    color: white;
    font-size: 13px;
    font-weight: 600;
}}
QFrame.card {{
    background: {COLORS['bg']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
}}
QLabel.cardTitle {{
    font-family: {SERIF};
    font-size: 15px;
    font-weight: 600;
}}
QLabel.cardSub {{
    color: {COLORS['muted']};
    font-size: 11.5px;
}}
QFrame.kpiCell {{
    border: none;
    border-right: 1px solid {COLORS['border']};
    border-bottom: 1px solid {COLORS['border']};
}}
QLabel.kpiNum {{
    font-family: {SERIF};
    font-size: 24px;
    font-weight: 600;
}}
QLabel.kpiNumRed {{
    font-family: {SERIF};
    font-size: 24px;
    font-weight: 600;
    color: {COLORS['brick']};
}}
QLabel.kpiLabel {{
    color: {COLORS['muted']};
    font-size: 11px;
}}
QFrame.alertItem {{
    border: none;
    border-right: 1px solid {COLORS['border']};
}}
QTableWidget {{
    border: none;
    gridline-color: {COLORS['border']};
    font-size: 12.5px;
    selection-background-color: {COLORS['accent_tint']};
    selection-color: {COLORS['ink']};
}}
QHeaderView::section {{
    background: {COLORS['bg']};
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    color: {COLORS['muted']};
    font-size: 11px;
    font-weight: 600;
    padding: 6px 8px;
    text-align: left;
}}
QStatusBadge {{
    border-radius: 3px;
}}
"""
