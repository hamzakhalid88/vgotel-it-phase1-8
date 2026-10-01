"""
Central configuration loader.

Reads config/app_settings.json for non-secret settings (numbering prefixes,
which DB dialect to target, paths, backup policy, etc). The DB password, if
the real SQL Server uses SQL auth instead of a trusted/Windows connection, is
read ONLY from the VGOTEL_DB_PASSWORD environment variable — it is never
written to the JSON file or hardcoded anywhere. See README.md "Connecting to
your real SQL Server" for how to switch dialect from sqlite -> mssql+pyodbc.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "config" / "app_settings.json"


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    company_name: str
    db_url: str
    dialect: str
    asset_prefix: str
    maintenance_prefix: str
    gate_pass_prefix: str
    invoice_prefix: str
    warranty_alert_days: int

    # Phase 9 — paths
    attachments_dir: str
    exports_dir: str
    backups_dir: str
    logs_dir: str

    # Phase 9 — backup policy
    auto_backup_enabled: bool
    auto_backup_interval_hours: int
    keep_last_n_backups: int

    # Phase 9 — ui prefs
    theme: str
    font_ui: str
    font_heading: str
    rows_per_page: int

    # ---------- Path helpers ----------
    def attachments_path(self) -> Path:
        return (BASE_DIR / self.attachments_dir).resolve()

    def exports_path(self) -> Path:
        return (BASE_DIR / self.exports_dir).resolve()

    def backups_path(self) -> Path:
        return (BASE_DIR / self.backups_dir).resolve()

    def logs_path(self) -> Path:
        return (BASE_DIR / self.logs_dir).resolve()

    def sqlite_file_path(self) -> Path | None:
        """Return resolved sqlite file path, or None for non-sqlite dialects."""
        if self.dialect != "sqlite":
            return None
        prefix = "sqlite:///"
        if self.db_url.startswith(prefix):
            return Path(self.db_url[len(prefix):])
        return None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _build_db_url(db_cfg: dict) -> str:
    dialect = db_cfg.get("dialect", "sqlite")

    if dialect == "sqlite":
        sqlite_path = BASE_DIR / db_cfg.get("sqlite_path", "data/vgotel_dev.db")
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{sqlite_path}"

    if dialect == "mssql+pyodbc":
        server = db_cfg["server"]
        database = db_cfg["database_name"]
        driver = quote_plus(db_cfg.get("driver", "ODBC Driver 17 for SQL Server"))

        if db_cfg.get("trusted_connection", True):
            return (
                f"mssql+pyodbc://@{server}/{database}"
                f"?driver={driver}&trusted_connection=yes"
            )

        username = quote_plus(db_cfg.get("username", ""))
        password = os.environ.get("VGOTEL_DB_PASSWORD", "")
        if not password:
            raise RuntimeError(
                "VGOTEL_DB_PASSWORD is not set. Export it in the environment "
                "before starting the app when using SQL authentication."
            )
        password = quote_plus(password)
        return (
            f"mssql+pyodbc://{username}:{password}@{server}/{database}"
            f"?driver={driver}"
        )

    raise ValueError(f"Unsupported database dialect: {dialect}")


def load_config() -> AppConfig:
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    db_cfg = raw["database"]
    numbering = raw["numbering"]
    paths = raw.get("paths", {})
    backup = raw.get("backup", {})
    ui = raw.get("ui", {})

    return AppConfig(
        app_name=raw.get("app_name", "Vgotel IT Console"),
        company_name=raw.get("company_name", "Vgotel"),
        db_url=_build_db_url(db_cfg),
        dialect=db_cfg.get("dialect", "sqlite"),
        asset_prefix=numbering.get("asset_prefix", "AST"),
        maintenance_prefix=numbering.get("maintenance_prefix", "MNT"),
        gate_pass_prefix=numbering.get("gate_pass_prefix", "GP"),
        invoice_prefix=numbering.get("invoice_prefix", "INV"),
        warranty_alert_days=raw.get("warranty_alert_days", 30),

        attachments_dir=paths.get("attachments_dir", "attachments"),
        exports_dir=paths.get("exports_dir", "exports"),
        backups_dir=paths.get("backups_dir", "backups"),
        logs_dir=paths.get("logs_dir", "logs"),

        auto_backup_enabled=backup.get("auto_backup_enabled", False),
        auto_backup_interval_hours=backup.get("auto_backup_interval_hours", 24),
        keep_last_n_backups=backup.get("keep_last_n_backups", 10),

        theme=ui.get("theme", "ledger"),
        font_ui=ui.get("font_ui", "Inter"),
        font_heading=ui.get("font_heading", "Source Serif 4"),
        rows_per_page=ui.get("rows_per_page", 50),
    )


# ---------------------------------------------------------------------------
# Saving (Phase 9 — Settings UI)
# ---------------------------------------------------------------------------

def save_config(cfg: AppConfig) -> None:
    """
    Persist editable fields of `cfg` back to app_settings.json.
    DB credentials are NEVER written (password stays in environment only).
    """
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    raw["app_name"] = cfg.app_name
    raw["company_name"] = cfg.company_name
    raw["warranty_alert_days"] = cfg.warranty_alert_days

    raw.setdefault("numbering", {})
    raw["numbering"]["asset_prefix"] = cfg.asset_prefix
    raw["numbering"]["maintenance_prefix"] = cfg.maintenance_prefix
    raw["numbering"]["gate_pass_prefix"] = cfg.gate_pass_prefix
    raw["numbering"]["invoice_prefix"] = cfg.invoice_prefix

    raw.setdefault("paths", {})
    raw["paths"]["attachments_dir"] = cfg.attachments_dir
    raw["paths"]["exports_dir"] = cfg.exports_dir
    raw["paths"]["backups_dir"] = cfg.backups_dir
    raw["paths"]["logs_dir"] = cfg.logs_dir

    raw.setdefault("backup", {})
    raw["backup"]["auto_backup_enabled"] = cfg.auto_backup_enabled
    raw["backup"]["auto_backup_interval_hours"] = cfg.auto_backup_interval_hours
    raw["backup"]["keep_last_n_backups"] = cfg.keep_last_n_backups

    raw.setdefault("ui", {})
    raw["ui"]["theme"] = cfg.theme
    raw["ui"]["font_ui"] = cfg.font_ui
    raw["ui"]["font_heading"] = cfg.font_heading
    raw["ui"]["rows_per_page"] = cfg.rows_per_page

    # Do NOT touch raw["database"] — dialect/server/db name only changed manually.

    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2)