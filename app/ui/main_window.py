from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from app.config import AppConfig
from app.services import permission_service
from app.ui.pages.assets_page import build_assets_page
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.categories_page import build_categories_page
from app.ui.pages.clients_page import build_clients_page
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.departments_page import build_departments_page
from app.ui.pages.devices_page import build_devices_page
from app.ui.pages.gate_pass_page import build_gate_pass_page
from app.ui.pages.invoice_page import build_invoice_page
from app.ui.pages.maintenance_page import build_maintenance_page
from app.ui.pages.placeholder_page import PlaceholderPage
from app.ui.pages.repair_history_page import RepairHistoryPage
from app.ui.pages.reports_page import ReportsHubPage
from app.ui.pages.technicians_page import build_technicians_page
from app.ui.pages.users_roles_page import build_users_roles_page
from app.ui.widgets.sidebar import NAV_GROUPS, Sidebar
from app.ui.widgets.topbar import TopBar

PAGE_TITLES = {key: label for _, items in NAV_GROUPS for key, label in items}

BUILT_KEYS = {
    "dashboard", "departments", "categories", "clients", "technicians", "assets", "devices",
    "maintenance", "repair_history", "gate_pass", "invoices", "reports", "settings",
}

PHASE_NOTE = {
    "users_roles": "Only an Administrator account can open Users & roles.",
    "settings": "Settings (company info, numbering, theme, backup) are built in Phase 9.",
}


class MainWindow(QWidget):
    def __init__(self, cfg: AppConfig, user_id: int, user_full_name: str, user_role: str, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.user_id = user_id
        self.user_role = user_role
        self.setWindowTitle(cfg.app_name)
        self.resize(1440, 900)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar(cfg.app_name, user_role, on_navigate=self._navigate)
        root.addWidget(self.sidebar)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        # Notification count reflects live overdue + warranty-expiring
        # totals rather than a hardcoded badge — see _initial_notification_count.
        self.topbar = TopBar(user_full_name, user_role, self._initial_notification_count())
        right.addWidget(self.topbar)

        self.stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}

        dashboard = DashboardPage(cfg.warranty_alert_days)
        self._pages["dashboard"] = dashboard
        self.stack.addWidget(dashboard)

        for key, builder in (
            ("departments", build_departments_page),
            ("categories", build_categories_page),
            ("clients", build_clients_page),
            ("technicians", build_technicians_page),
        ):
            page = builder(self.user_id, user_role, parent=self)
            self._pages[key] = page
            self.stack.addWidget(page)

        assets_page = build_assets_page(cfg, self.user_id, user_role, parent=self)
        self._pages["assets"] = assets_page
        self.stack.addWidget(assets_page)

        devices_page = build_devices_page(self.user_id, user_role, parent=self)
        self._pages["devices"] = devices_page
        self.stack.addWidget(devices_page)

        maintenance_page = build_maintenance_page(cfg, self.user_id, user_role, parent=self)
        self._pages["maintenance"] = maintenance_page
        self.stack.addWidget(maintenance_page)

        repair_history_page = RepairHistoryPage()
        self._pages["repair_history"] = repair_history_page
        self.stack.addWidget(repair_history_page)

        gate_pass_page = build_gate_pass_page(user_role, parent=self)
        self._pages["gate_pass"] = gate_pass_page
        self.stack.addWidget(gate_pass_page)

        invoice_page = build_invoice_page(cfg, self.user_id, user_role, parent=self)
        self._pages["invoices"] = invoice_page
        self.stack.addWidget(invoice_page)

        reports_page = ReportsHubPage(user_full_name, can_export=permission_service.can_export(user_role), parent=self)
        self._pages["reports"] = reports_page
        self.stack.addWidget(reports_page)

        # Users & roles is only ever constructed for an Administrator — for
        # every other role it isn't in the sidebar at all (Sidebar filters
        # on permission_service.can_view_page), and if _navigate is ever
        # called with "users_roles" directly it safely no-ops because the
        # key won't be in self._pages.
        if permission_service.can_manage_users(user_role):
            self._pages["users_roles"] = build_users_roles_page(self.user_id, user_role, parent=self)
            self.stack.addWidget(self._pages["users_roles"])
        if permission_service.can_view_page(user_role, "settings"):
            self._pages["settings"] = SettingsPage(cfg)
            self.stack.addWidget(self._pages["settings"])

        for key, title in PAGE_TITLES.items():
            if key in self._pages or key in BUILT_KEYS:
                continue
            page = PlaceholderPage(title, PHASE_NOTE.get(key, "Coming in a later phase."))
            self._pages[key] = page
            self.stack.addWidget(page)

        right.addWidget(self.stack, 1)
        right_wrap = QWidget()
        right_wrap.setLayout(right)
        root.addWidget(right_wrap, 1)

    def _initial_notification_count(self) -> int:
        from app.db.base import session_scope
        from app.services import dashboard_service
        with session_scope() as s:
            kpis = dashboard_service.get_kpis(s, self.cfg.warranty_alert_days)
            warranty = dashboard_service.get_warranty_expiring(s, self.cfg.warranty_alert_days)
        return kpis["overdue_repairs"] + len(warranty)

    def _navigate(self, key: str):
        page = self._pages.get(key)
        if page is not None:
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()
            self.stack.setCurrentWidget(page)
            self.topbar.set_breadcrumb(PAGE_TITLES.get(key, key.title()))
