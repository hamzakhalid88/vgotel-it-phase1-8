"""
Phase 6 — Attachments.

Bill images are copied into an organized local folder tree rather than
stored in the database (spec section 56 explicitly asks for this — "Do
not store huge files directly in database"). Maintenance.bill_image holds
the path relative to the attachments root, so the app stays portable
between machines/dev-vs-prod as long as the attachments root moves with
the database.
"""
from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path

ATTACHMENTS_ROOT = Path(__file__).resolve().parent.parent.parent / "attachments"


def store_bill_image(source_path: str, maintenance_number: str, entry_date: dt.date) -> str:
    """Copies source_path into Attachments/<year>/Maintenance/<MNT-number>/
    and returns the path relative to ATTACHMENTS_ROOT (what gets saved on
    Maintenance.bill_image)."""
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"File not found: {source_path}")

    year = entry_date.year if entry_date else dt.date.today().year
    dest_dir = ATTACHMENTS_ROOT / str(year) / "Maintenance" / maintenance_number
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / src.name
    if dest_path.exists():
        stem, suffix = dest_path.stem, dest_path.suffix
        n = 1
        while dest_path.exists():
            dest_path = dest_dir / f"{stem}_{n}{suffix}"
            n += 1

    shutil.copy2(src, dest_path)
    return str(dest_path.relative_to(ATTACHMENTS_ROOT))


def resolve(relative_path: str) -> Path:
    return ATTACHMENTS_ROOT / relative_path


def remove_bill_image(relative_path: str) -> None:
    p = resolve(relative_path)
    if p.exists():
        p.unlink()
