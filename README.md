# Vgotel IT Console

A working start on the Enterprise IT Asset & Maintenance Management System
brief, built in the **Ledger** visual design (the one picked from the five
preview mockups). This now covers Phases 1–8 of the brief's own 9-phase plan
(section 72) — real, tested code, not a mockup — plus the groundwork
(migrations, schema-introspection script) Phase 9 onward will build on.

## What's actually working right now

- Config layer that targets local SQLite for development and can be pointed
  at the real SQL Server by editing one file (no code changes).
- SQLAlchemy models for every existing table, a seed script with realistic
  hotel-IT demo data, and a rotating file logger.
- Login, with bcrypt password hashing and audit-logged attempts (success
  and failure both).
- Concurrency-safe AST-/MNT-/GP-/INV- number generation.
- The main shell (sidebar, top bar, breadcrumb) and a **fully live Dashboard**
  — every KPI, chart, table and warranty/overdue alert is a real query
  against the database, not placeholder numbers.
- **Departments, Categories, Clients and Technicians** — full list, search,
  add and edit screens, each backed by real queries (usage counts per
  department/category, live job counts and repair spend per technician).
  Deactivating or deleting a record that's still in use is blocked with a
  clear message instead of silently breaking references (spec sections
  15/38), and every create/update/status-change is written to the audit log.
- **Assets and Devices** — search plus a status filter, add/edit forms with
  real validation (unique serial numbers, non-negative cost, valid dates),
  and an **Asset detail view** with general info, assignment, purchase info,
  a live repair-cost summary and a chronological repair timeline built from
  real repair-history rows (spec section 11). Deactivating an Assigned asset
  or deleting an in-use device is blocked the same way as Phase 3.
- **Maintenance workflow** — a real state machine (Received → Assigned →
  In Repair → Completed → Returned → Closed, spec section 17), each step
  its own guarded action so a case can't skip a stage. Creating a case
  auto-generates both the Maintenance number and a Gate Pass number and
  flips the asset to "Under Repair"; completing one writes a real
  repair-history row and bumps the asset's repair count (spec section 24);
  returning it flips the asset status back. The tabbed detail dialog (spec
  section 18: Overview/Problem/Repair details/Technician/Warranty/
  Financial/Attachments/History) reads its History tab straight from the
  audit log. **Repair history** and **Gate pass** each get their own page —
  a global searchable repair log with computed totals, and a printable-style
  gate pass card per case.
- **Invoices, warranty status and attachments** — an invoice is generated
  from any Completed-or-later case (blocked until then, and generating twice
  just returns the same number instead of duplicating it), with its own
  printable card matching the Gate Pass card's style. Warranty status
  (Active / Expiring soon / Expired) is computed everywhere a warranty date
  appears — the Dashboard, the Maintenance detail's Warranty tab, and the
  Invoice card — rather than just showing a raw date. Bill images can be
  uploaded, previewed and removed from the Maintenance detail's Attachments
  tab; files are copied into `attachments/<year>/Maintenance/<MNT-number>/`
  rather than stored in the database (spec section 56).
- **Reports** — 14 reports across all four categories the brief asks for
  (Asset/Maintenance/Financial/Warranty, spec section 27), one generic
  viewer and exporter instead of a bespoke screen per report. Every report
  exports to real **CSV, Excel (openpyxl) and PDF (reportlab)** with a
  letterhead, generated-by/timestamp, totals and page numbers (spec section
  63) — not stubs; `scripts/verify_phase7.py` runs every single registered
  report and checks the export files are real and non-empty. A few of the
  brief's report names map onto one parameterized report rather than a
  separate screen each — e.g. Daily/Monthly/Yearly Maintenance are all the
  one date-range "Maintenance in date range" report — which covers more
  ground with less duplication.
- **Roles & permissions, Users & roles, Audit log** — four roles
  (Administrator / IT Manager / IT Technician / Viewer, spec section 31)
  enforced in two places: the sidebar hides pages a role can't open, and
  every mutating service function takes the acting role and refuses the
  call server-side if it's not allowed — not just a hidden button, spec's
  own "enforce at service/business layer, not only UI". The exact
  page-access and write-access matrix per role is documented (and easy to
  adjust) in `app/services/permission_service.py`. Administrator gets a
  real **Users & roles** page — create/edit/deactivate users, reset
  passwords, with a guard against ever locking out the last active
  Administrator — plus an **Audit log** tab: a searchable, filterable
  browser over every create/update/status-change/login the system has
  recorded, rather than only being visible per-record on the Maintenance
  detail's History tab.
- Every other sidebar item still opens an honest "built in Phase N"
  placeholder instead of a broken page.

Screenshots of this actually running are attached alongside this project,
including the same screen shown to three different roles side by side —
narrower sidebar for IT Technician, read-only Departments for Viewer, an
export-hidden report for Viewer.

**Bug fixed this drop:** a real, pre-existing Qt rendering issue in
`crud_list_page.py` — a table that had been refreshed once while hidden
(every list page, at app startup) then refreshed again on first being
shown could leave a ghost copy of its row-action buttons floating over
the wrong column. Reproduced it on Departments (an already-shipped
Phase 3 page, not something new from this drop), root-caused it to
`QTableWidget` not fully discarding old cell widgets when a row is
reused, and fixed it by clearing the table's rows before repopulating
them on every refresh. Every list screen benefits, not just Phase 8's.

Screenshots of this actually running are attached alongside this project.

## Quick start

```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m scripts.verify_core     # seeds the local DB and proves Phase 1-2 works
python -m scripts.verify_phase3   # proves create/update/deactivate + in-use guards
python -m scripts.verify_phase4   # proves asset/device CRUD + duplicate-serial guard
python -m scripts.verify_phase5   # proves the full maintenance workflow end to end
python -m scripts.verify_phase6   # proves invoice generation + warranty status + attachments
python -m scripts.verify_phase7   # runs every report + checks CSV/Excel/PDF exports are real
python -m scripts.verify_phase8   # proves the full role/permission matrix + user management
python app/main.py                # launch the app
```

Demo accounts (local dev data only — see `app/db/seed.py`):

| Username    | Password      | Role           |
|-------------|---------------|----------------|
| admin       | Admin@123     | Administrator  |
| z.manager   | Manager@123   | IT Manager     |
| b.khan      | Tech@123      | IT Technician  |
| viewer      | Viewer@123    | Viewer         |

## Fonts

The Ledger design uses **Inter** (UI/body) and **Source Serif 4** (headings).
Both are free Google Fonts. Install them on the machine running the app for
pixel-accurate typography; without them Qt falls back to Segoe UI / Georgia
automatically, which is still readable.

## Connecting to your real SQL Server

1. Run `migrations/001_review_existing_schema.sql` against the real
   `Vgotel_IT_DB` (or `python scripts/introspect_mssql_schema.py --server ...`
   from a machine that can reach it — this sandbox can't). Compare the
   result against `app/db/models.py` and adjust column names/types to match.
2. Run `migrations/002_new_tables.sql` — it only adds new tables
   (`audit_logs`, `app_settings`, `number_sequences`) and three new
   columns on the existing `maintenance` table for Gate Pass fields
   (`gate_pass_reason`, `authorized_by`, `actual_return_date`); it never
   touches existing data.
3. Edit `config/app_settings.json`:
   ```json
   "database": {
     "dialect": "mssql+pyodbc",
     "server": "YOUR_SERVER",
     "database_name": "Vgotel_IT_DB",
     "driver": "ODBC Driver 17 for SQL Server",
     "trusted_connection": true
   }
   ```
   If you need SQL auth instead of a trusted connection, set
   `"trusted_connection": false`, add `"username"`, and export
   `VGOTEL_DB_PASSWORD` in the environment — the password is never written
   to a file.
4. Install the ODBC Driver 17 (or 18) for SQL Server on the machine running
   the app, plus `pip install pyodbc`.
5. Do **not** run `app/db/seed.py` against it — it refuses to run against
   anything other than the sqlite dialect on purpose.

## Project layout

```
app/
  config.py, logging_setup.py       Phase 1
  db/                                 models, engine/session, seed data
  services/                           auth, numbering, dashboard queries,
                                       directory (dept/category/client/tech),
                                       asset_service, device_service,
                                       maintenance_service (workflow engine),
                                       repair_history_service, invoice_service,
                                       attachment_service, report_service (14 reports),
                                       export_service (CSV/Excel/PDF),
                                       permission_service (role matrix + guard),
                                       user_service, audit_log_service, audit_service
  ui/
    theme.py                          Ledger design tokens as a Qt stylesheet
    widgets/                          sidebar (role-filtered), topbar,
                                       bar/donut chart widgets,
                                       crud_list_page + form_dialog (generic CRUD UI,
                                       can_write-gated), asset_detail_dialog
                                       (repair timeline view), maintenance_detail_dialog
                                       (tabbed workflow + invoice + attachments view)
    pages/dashboard_page.py           the fully-working Dashboard
    pages/departments_page.py, categories_page.py,
    pages/clients_page.py, technicians_page.py   Phase 3 screens
    pages/assets_page.py, devices_page.py        Phase 4 screens
    pages/maintenance_page.py, repair_history_page.py,
    pages/gate_pass_page.py                      Phase 5 screens
    pages/invoice_page.py                        Phase 6 screen (printable card)
    pages/reports_page.py                        Phase 7 (hub + generic viewer/exporter)
    pages/users_roles_page.py                    Phase 8 (Users tab + Audit log tab)
    pages/placeholder_page.py         honest "coming in Phase N" page
    login_window.py, main_window.py, splash.py
migrations/                          SQL for the real SQL Server
scripts/
  verify_core.py                     non-GUI proof the Phase 1-2 layer works
  verify_phase3.py                   non-GUI proof CRUD + in-use guards work
  verify_phase4.py                   non-GUI proof asset/device CRUD + guards work
  verify_phase5.py                   non-GUI proof of the full workflow + side effects
  verify_phase6.py                   non-GUI proof of invoicing + warranty + attachments
  verify_phase7.py                   non-GUI proof every report runs + exports are real
  verify_phase8.py                   non-GUI proof of the full role/permission matrix
  screenshot_app.py                  headless screenshot generator (offscreen Qt)
  introspect_mssql_schema.py         schema-reconciliation helper
attachments/                         bill images, created on first upload (gitignored)
exports/                             report exports land here by default (gitignored)
```

## Roadmap (matches the brief's own section 72 phases)

| Phase | Scope | Status |
|-------|-------|--------|
| 1 – 2 | Architecture, auth, shell, Dashboard | **Done** |
| 3 | Departments, Categories, Clients, Technicians (CRUD) | **Done** |
| 4 | Assets, Devices, assignment, asset detail/timeline | **Done** |
| 5 | Maintenance workflow, Gate Pass, Repair history | **Done** |
| 6 | Invoices, Warranty detail, Attachments | **Done** |
| 7 | Reports library, Excel/PDF export, printing | **Done** |
| 8 | Granular roles & permissions, full Audit log UI | **Done, this drop** |
| 9 | Settings UI, Backup, Windows installer | Next |

Honest scope note: a production rollout also needs the real column-name
reconciliation above, a decision on the three legacy sequence tables (see
the comment in `migrations/002_new_tables.sql`), and a Windows-side install/
packaging step (e.g. PyInstaller + an installer builder) — none of which
can be finished from this sandbox since it can't reach your SQL Server or
build a Windows executable. Also: the brief's "Approve" and "Print" granular
permissions (section 31) aren't separately enforced — there's no distinct
approval step in the workflow to gate, and Print isn't a separate action
from Export in this build. Documented in `permission_service.py` rather
than silently assumed. Say which phase to build next and we'll keep going
the same way: real code, tested, then the next module.
