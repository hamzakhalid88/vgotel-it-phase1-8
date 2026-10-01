"""
Populates data/vgotel_dev.db with realistic demo data so every dashboard
query has real rows to compute against. This never touches a real
Vgotel_IT_DB — it only runs against the local sqlite dialect. Safe to
re-run: it clears and rebuilds the local dev tables each time (spec
section 67 — seed/test data must stay separate from production, which is
exactly what running this only against sqlite guarantees).
"""
from __future__ import annotations

import datetime as dt
import random

from app.config import load_config
from app.db.base import Base, init_engine, session_scope
from app.db.models import (
    Asset, AssetRepairHistory, Category, Client, Department, Device,
    Maintenance, Technician, User,
)
from app.services.auth_service import hash_password
from app.services import numbering_service

random.seed(42)

DEPARTMENTS = [
    ("Front Office", "Ground Floor", "021-111-020-020"),
    ("Housekeeping", "2nd Floor", "021-111-020-021"),
    ("Kitchen & F&B", "Basement", "021-111-020-022"),
    ("Sales & Admin", "3rd Floor", "021-111-020-023"),
    ("Engineering", "Basement", "021-111-020-024"),
]

CATEGORIES = ["Laptop", "Desktop", "Printer", "Network Device", "POS Terminal"]

TECHNICIANS = [
    ("Bilal Khan", "0301-2345678", "bilal@techfixsolutions.pk", "TechFix Solutions", "021-345-1122"),
    ("Sana Tariq", "0322-9988776", "sana@rapiditrepairs.pk", "Rapid IT Repairs", "021-566-3344"),
    ("Waqas Ali", "0345-1122334", "waqas@netcareservices.pk", "NetCare Services", "021-778-9900"),
]

DEVICE_MODELS = {
    "Laptop": ["Dell Latitude 5420", "Lenovo ThinkPad T14", "HP EliteBook 840"],
    "Desktop": ["HP ProDesk 400 G7", "Dell OptiPlex 3080"],
    "Printer": ["Canon imageRunner 2530", "HP LaserJet Pro M404", "Epson L3210"],
    "Network Device": ["Cisco Catalyst 24P", "TP-Link TL-SG1024", "Ubiquiti UniFi AP"],
    "POS Terminal": ["Epson TM-T88V POS", "Verifone MX925"],
}

EMPLOYEE_FIRST = ["Ahmed", "Ayesha", "Bilal", "Farah", "Hamza", "Iqra", "Kashif",
                  "Mariam", "Nabeel", "Rabia", "Saad", "Tariq", "Usman", "Zara"]
EMPLOYEE_LAST = ["Raza", "Khan", "Malik", "Siddiqui", "Iqbal", "Farooq", "Sheikh"]

ISSUES = [
    "Not powering on", "Screen flickering", "Overheating", "Slow performance",
    "Printer paper jam / print quality poor", "No network connectivity",
    "Battery not charging", "Keyboard keys unresponsive", "Blue screen on boot",
]


def _rand_date(days_back_min: int, days_back_max: int) -> dt.date:
    return dt.date.today() - dt.timedelta(days=random.randint(days_back_min, days_back_max))


def seed():
    cfg = load_config()
    if cfg.dialect != "sqlite":
        raise RuntimeError("Refusing to seed a non-sqlite target. Seed data is for local dev only.")

    init_engine(cfg.db_url)
    Base.metadata.drop_all(bind=_engine_for_drop())
    Base.metadata.create_all(bind=_engine_for_drop())

    with session_scope() as s:
        depts = [Department(name=n, location=l, phone=p) for n, l, p in DEPARTMENTS]
        s.add_all(depts)
        s.flush()

        cats = [Category(name=n, description=f"{n} devices and peripherals") for n in CATEGORIES]
        s.add_all(cats)
        s.flush()

        techs = [
            Technician(name=n, phone=p, email=e, shop_name=shop, shop_contact=c)
            for n, p, e, shop, c in TECHNICIANS
        ]
        s.add_all(techs)
        s.flush()

        clients = []
        for i in range(28):
            dept = random.choice(depts)
            name = f"{random.choice(EMPLOYEE_FIRST)} {random.choice(EMPLOYEE_LAST)}"
            clients.append(Client(
                name=name, department_id=dept.id,
                phone=f"03{random.randint(10,49)}-{random.randint(1000000,9999999)}",
                email=f"{name.lower().replace(' ', '.')}@vgotel.pk",
                designation=random.choice(["Executive", "Supervisor", "Officer", "Team Lead"]),
            ))
        s.add_all(clients)
        s.flush()

        devices = []
        for cat in cats:
            for model in DEVICE_MODELS[cat.name]:
                for _ in range(random.randint(3, 6)):
                    dept = random.choice(depts)
                    devices.append(Device(
                        model=model, category_id=cat.id, department_id=dept.id,
                        serial_number=f"SN-{random.randint(100000, 999999)}",
                        purchase_date=_rand_date(200, 1100),
                        status=random.choices(
                            ["Available", "Assigned", "Under Repair"], weights=[2, 6, 1]
                        )[0],
                    ))
        s.add_all(devices)
        s.flush()

        statuses = ["Assigned"] * 65 + ["Available"] * 18 + ["Under Repair"] * 5 + \
                   ["Retired"] * 7 + ["Inactive"] * 5
        random.shuffle(statuses)

        assets = []
        for i, status in enumerate(statuses, start=1):
            dept = random.choice(depts)
            device = random.choice(devices)
            assets.append(Asset(
                asset_number=numbering_service.next_asset_number(s, cfg.asset_prefix),
                asset_type=device.category.name if device.category else device.model,
                serial_number=f"AST-SN-{100000+i}",
                department_id=dept.id,
                client_id=random.choice(clients).id if status == "Assigned" else None,
                device_id=device.id,
                floor=dept.location,
                status=status,
                purchase_date=_rand_date(60, 1200),
                vendor=random.choice(["Continental Traders", "AlphaTech Supplies", "Karachi IT Mart"]),
                purchase_cost=round(random.uniform(25000, 220000), -2),
                repair_count=0,
            ))
        s.add_all(assets)
        s.flush()

        # Maintenance history over the last 6 months, spanning every real
        # workflow stage so the status filter has something in each bucket.
        maint_statuses_recent = (
            ["Closed"] * 3 + ["Returned"] * 2 + ["Completed"] * 3
            + ["In Repair"] * 2 + ["Assigned"] * 1 + ["Received"] * 1
        )
        maintenance_rows = []
        for month_back in range(6):
            for _ in range(random.randint(5, 9)):
                asset = random.choice(assets)
                tech = random.choice(techs)
                status = random.choice(maint_statuses_recent)
                today = dt.date.today()
                entry = today - dt.timedelta(days=month_back * 30 + random.randint(0, 27))
                completed = None
                actual_return = None
                warranty_months = random.choice([0, 3, 6, 12])
                warranty_until = None
                cost = None
                is_done = status in ("Completed", "Returned", "Closed")
                technician_id = tech.id if status != "Received" else None

                if is_done:
                    completed = min(entry + dt.timedelta(days=random.randint(1, 6)), today)
                    expected_return = completed
                    cost = round(random.uniform(1500, 22000), -2)
                    if warranty_months:
                        warranty_until = completed + dt.timedelta(days=30 * warranty_months)
                    if status in ("Returned", "Closed"):
                        actual_return = completed + dt.timedelta(days=random.randint(0, 2))
                elif status == "In Repair" and random.random() < 0.4:
                    # A genuinely overdue case — still open, past its due date.
                    # display_status derives "Overdue" from this automatically.
                    expected_return = today - dt.timedelta(days=random.randint(1, 12))
                else:
                    # Received / Assigned / In Repair — still within its window.
                    expected_return = today + dt.timedelta(days=random.randint(2, 9))

                maintenance_rows.append(Maintenance(
                    maintenance_number=numbering_service.next_maintenance_number(s, cfg.maintenance_prefix),
                    gate_pass_number=numbering_service.next_gate_pass_number(s, cfg.gate_pass_prefix),
                    asset_id=asset.id,
                    department_id=asset.department_id,
                    category_id=asset.device.category_id if asset.device else None,
                    technician_id=technician_id,
                    employee_name=asset.client.name if asset.client else None,
                    device_model=asset.device.model if asset.device else asset.asset_type,
                    issue=random.choice(ISSUES),
                    repair_details="Diagnosed and repaired on site." if is_done else None,
                    cost=cost,
                    status=status,
                    gate_pass_reason="Sent for external repair" if is_done or status == "In Repair" else None,
                    authorized_by="Zeeshan Ahmed" if is_done or status == "In Repair" else None,
                    technician_shop=tech.shop_name if technician_id else None,
                    technician_contact=tech.shop_contact if technician_id else None,
                    entry_date=entry,
                    expected_return_date=expected_return,
                    actual_return_date=actual_return,
                    completed_date=completed,
                    warranty_months=warranty_months or None,
                    warranty_until=warranty_until,
                    is_completed=is_done,
                ))
        s.add_all(maintenance_rows)
        s.flush()

        # A handful of warranties deliberately expiring soon, so the
        # "Warranty expiring" widget always has something real to show.
        soon_targets = [m for m in maintenance_rows if m.is_completed][:4]
        for m, days_left in zip(soon_targets, [6, 12, 18, 25]):
            m.warranty_until = dt.date.today() + dt.timedelta(days=days_left)

        # Repair history + repair_count/last_repair_date rollups
        for m in maintenance_rows:
            if m.is_completed:
                s.add(AssetRepairHistory(
                    asset_id=m.asset_id, repair_date=m.completed_date, issue=m.issue,
                    repair_details=m.repair_details, cost=m.cost,
                    technician_id=m.technician_id, status="Completed",
                ))
                asset = s.get(Asset, m.asset_id)
                asset.repair_count += 1
                if not asset.last_repair_date or m.completed_date > asset.last_repair_date:
                    asset.last_repair_date = m.completed_date
                if asset.status not in ("Retired", "Inactive"):
                    pass  # leave current status as-is; repair is historical

        users = [
            User(username="admin", password_hash=hash_password("Admin@123"),
                 full_name="Zeeshan Ahmed", role="Administrator"),
            User(username="z.manager", password_hash=hash_password("Manager@123"),
                 full_name="Zeeshan Ahmed", role="IT Manager"),
            User(username="b.khan", password_hash=hash_password("Tech@123"),
                 full_name="Bilal Khan", role="IT Technician"),
            User(username="viewer", password_hash=hash_password("Viewer@123"),
                 full_name="Front Desk Viewer", role="Viewer"),
        ]
        s.add_all(users)

    print("Seed complete:")
    print(f"  departments={len(depts)} categories={len(cats)} technicians={len(techs)}")
    print(f"  clients={len(clients)} devices={len(devices)} assets={len(assets)}")
    print(f"  maintenance={len(maintenance_rows)} users={len(users)}")


def _engine_for_drop():
    from app.db.base import get_engine
    return get_engine()


if __name__ == "__main__":
    seed()
