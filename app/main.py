from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.config import load_config
from app.db.base import init_engine
from app.logging_setup import get_logger, setup_logging
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow
from app.ui.splash import make_splash
from app.ui.theme import QSS


def main():
    setup_logging()
    log = get_logger()
    log.info("Application starting")

    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)

    splash = make_splash()
    splash.show()
    app.processEvents()

    cfg = load_config()
    log.info("Config loaded: dialect=%s app_name=%s", cfg.dialect, cfg.app_name)
    init_engine(cfg.db_url)

    state = {"login": None, "main": None}

    def show_login():
        splash.close()

        def on_success(user_id, full_name, role):
            log.info("Login success: user_id=%s role=%s", user_id, role)
            state["main"] = MainWindow(cfg, user_id, full_name, role)
            state["main"].show()
            state["login"].close()

        state["login"] = LoginWindow(cfg.app_name, on_success)
        state["login"].show()

    QTimer.singleShot(600, show_login)

    exit_code = app.exec()

    # ------------------------------------------------------------------
    # Phase 9: Auto-backup on exit (SQLite only, opt-in via Settings UI)
    # ------------------------------------------------------------------
    if cfg.auto_backup_enabled and cfg.dialect == "sqlite":
        db_file = cfg.sqlite_file_path()
        if db_file and db_file.exists():
            try:
                from app.services.backup_service import backup_database
                path = backup_database(
                    str(db_file),
                    str(cfg.backups_path()),
                    cfg.keep_last_n_backups,
                )
                log.info("Auto-backup on exit created: %s", path)
            except Exception as e:
                log.error("Auto-backup on exit failed: %s", e)
        else:
            log.warning("Auto-backup skipped: sqlite file not found")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()