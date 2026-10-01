"""
Phase 9 — SQLite backup / restore service.

Uses Python's built-in sqlite3.backup() API, which produces a consistent
snapshot even while the app has the database open. Old backups are pruned
automatically, keeping only the newest N (configurable in Settings UI).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.logging_setup import get_logger

log = get_logger()


def backup_database(db_path: str, backups_dir: str, keep_last_n: int = 10) -> str:
    """
    Create a consistent SQLite backup.

    Returns the path of the new backup file.
    Raises FileNotFoundError if source DB is missing.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    backups_dir = Path(backups_dir)
    backups_dir.mkdir(parents=True, exist_ok=True)

    # Windows-safe timestamp (avoid %-d / %-H which crash on Windows)
    now = datetime.now()
    timestamp = (
        f"{now.year:04d}{now.month:02d}{now.day:02d}"
        f"_{now.hour:02d}{now.minute:02d}{now.second:02d}"
    )
    backup_path = backups_dir / f"vgotel_backup_{timestamp}.db"

    source = sqlite3.connect(str(db_path))
    dest = sqlite3.connect(str(backup_path))
    try:
        source.backup(dest)
    finally:
        source.close()
        dest.close()

    log.info("Backup created: %s", backup_path)
    _prune_old_backups(backups_dir, keep_last_n)
    return str(backup_path)


def _prune_old_backups(backups_dir: Path, keep_last_n: int) -> None:
    """Delete oldest backups so only the newest `keep_last_n` remain."""
    if keep_last_n <= 0:
        return
    files = sorted(
        backups_dir.glob("vgotel_backup_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in files[keep_last_n:]:
        try:
            old.unlink()
            log.info("Pruned old backup: %s", old)
        except OSError as e:
            log.warning("Could not delete %s: %s", old, e)


def restore_database(backup_path: str, db_path: str) -> None:
    """
    Restore a database from backup. The app must be closed / engine disposed
    before calling this.
    """
    backup_path = Path(backup_path)
    db_path = Path(db_path)
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    source = sqlite3.connect(str(backup_path))
    dest = sqlite3.connect(str(db_path))
    try:
        source.backup(dest)
    finally:
        source.close()
        dest.close()
    log.info("Database restored from %s to %s", backup_path, db_path)