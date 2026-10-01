"""
Phase 8 — Roles & permissions.

The brief names four roles and describes their scope in one line each
(section 31): Administrator (full access), IT Manager (Assets +
Maintenance + Reports), IT Technician (Maintenance + Assets), Viewer
(read-only). It doesn't spell out create/edit/delete granularity per
role beyond that, so the matrices below are this project's concrete,
documented interpretation of those four lines — adjust them here, in
one place, if the real policy differs.

Two enforcement points use this module:
  1. UI — Sidebar hides pages a role can't open; CrudListPage-based pages
     and the Maintenance/Invoice dialogs hide Add/Edit/Delete/workflow
     buttons when can_write() is False (spec: "hide unauthorized menu
     items").
  2. Service layer — every mutating function in directory_service,
     asset_service, device_service, maintenance_service and
     invoice_service takes an `actor_role` argument and calls
     require_write() as its first line, so the check holds even if a
     caller bypasses the UI entirely (spec: "enforce permissions at
     service/business layer, not only UI").

Not implemented: the "Approve" and "Print" permissions the brief also
lists (section 31). There's no distinct approval step anywhere in the
workflow to gate, and Print isn't a separate action from Export in this
build — noted here rather than silently assumed.
"""
from __future__ import annotations

ROLES = ["Administrator", "IT Manager", "IT Technician", "Viewer"]

ADMIN_ONLY_PAGES = {"users_roles", "settings"}

# Pages each role can navigate to at all. "dashboard" is always included.
PAGE_ACCESS: dict[str, set[str]] = {
    "Administrator": {
        "dashboard", "departments", "categories", "clients", "technicians",
        "assets", "devices", "maintenance", "repair_history", "gate_pass",
        "invoices", "reports", "users_roles", "settings",
    },
    "IT Manager": {
        "dashboard", "departments", "categories", "clients", "technicians",
        "assets", "devices", "maintenance", "repair_history", "gate_pass",
        "invoices", "reports",
    },
    "IT Technician": {
        "dashboard", "assets", "devices", "maintenance", "repair_history", "gate_pass",
    },
    "Viewer": {
        "dashboard", "departments", "categories", "clients", "technicians",
        "assets", "devices", "maintenance", "repair_history", "gate_pass",
        "invoices", "reports",
    },
}

# Broad write areas. "directory" covers Departments/Categories/Clients/Technicians.
WRITE_AREAS = {"directory", "assets", "devices", "maintenance", "invoices", "users"}

CAN_WRITE: dict[str, set[str]] = {
    "Administrator": set(WRITE_AREAS),
    "IT Manager": {"directory", "assets", "devices", "maintenance", "invoices"},
    "IT Technician": {"assets", "maintenance"},
    "Viewer": set(),
}

CAN_EXPORT: set[str] = {"Administrator", "IT Manager"}


class PermissionError(Exception):
    pass


def can_view_page(role: str, page_key: str) -> bool:
    if page_key == "dashboard":
        return True
    return page_key in PAGE_ACCESS.get(role, set())


def can_write(role: str, area: str) -> bool:
    if area not in WRITE_AREAS:
        raise ValueError(f"Unknown write area: {area!r}")
    return area in CAN_WRITE.get(role, set())


def can_export(role: str) -> bool:
    return role in CAN_EXPORT


def can_manage_users(role: str) -> bool:
    return role == "Administrator"


def require_write(role: str, area: str) -> None:
    """Service-layer guard — raises PermissionError instead of silently
    allowing a mutation a role shouldn't be able to make. Call this as
    the first line of every create/update/delete/status-change function."""
    if not can_write(role, area):
        raise PermissionError(f"{role} does not have write access to {area}.")
