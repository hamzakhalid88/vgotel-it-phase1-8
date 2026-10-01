"""
ORM models.

Column names here are a reasonable-best-guess mapping onto the table list
given in the brief (assets, devices, categories, clients, departments,
maintenance, technicians, users, asset_repair_history, gate_pass_sequence,
gp_sequence, invoice_sequence) using the business fields the brief itself
names in sections 9-20. The brief does not give exact column definitions,
so this is the assumption to reconcile against the real database — run
scripts/introspect_mssql_schema.py against the real Vgotel_IT_DB and diff
its output against this file before pointing the app at production. Tables
marked NEW are additions the brief asks for (sections 32, 46, 62) that did
not exist in the original table list.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    location: Mapped[Optional[str]] = mapped_column(String(120))
    phone: Mapped[Optional[str]] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(default=True)

    clients: Mapped[list["Client"]] = relationship(back_populates="department")
    devices: Mapped[list["Device"]] = relationship(back_populates="department")
    assets: Mapped[list["Asset"]] = relationship(back_populates="department")


class Client(Base):
    """Employee / staff member an asset can be assigned to."""
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"))
    phone: Mapped[Optional[str]] = mapped_column(String(40))
    email: Mapped[Optional[str]] = mapped_column(String(120))
    designation: Mapped[Optional[str]] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(default=True)

    department: Mapped[Optional["Department"]] = relationship(back_populates="clients")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))


class Technician(Base):
    __tablename__ = "technicians"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[Optional[str]] = mapped_column(String(40))
    email: Mapped[Optional[str]] = mapped_column(String(120))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    shop_name: Mapped[Optional[str]] = mapped_column(String(120))
    shop_contact: Mapped[Optional[str]] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(default=True)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(150))
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"))
    serial_number: Mapped[Optional[str]] = mapped_column(String(120), unique=True)
    purchase_date: Mapped[Optional[dt.date]]
    status: Mapped[str] = mapped_column(String(30), default="Available")

    category: Mapped[Optional["Category"]] = relationship()
    department: Mapped[Optional["Department"]] = relationship(back_populates="devices")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_number: Mapped[str] = mapped_column(String(20), unique=True)  # AST-000001
    asset_type: Mapped[str] = mapped_column(String(100))
    serial_number: Mapped[str] = mapped_column(String(120), unique=True)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"))
    client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id"))
    device_id: Mapped[Optional[int]] = mapped_column(ForeignKey("devices.id"))
    floor: Mapped[Optional[str]] = mapped_column(String(40))
    # Available | Assigned | Under Repair | Inactive | Lost | Retired | Scrapped
    status: Mapped[str] = mapped_column(String(30), default="Available")
    purchase_date: Mapped[Optional[dt.date]]
    vendor: Mapped[Optional[str]] = mapped_column(String(150))
    purchase_cost: Mapped[Optional[float]]
    repair_count: Mapped[int] = mapped_column(default=0)
    last_repair_date: Mapped[Optional[dt.date]]
    is_active: Mapped[bool] = mapped_column(default=True)  # soft delete, spec section 38
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )

    department: Mapped[Optional["Department"]] = relationship(back_populates="assets")
    client: Mapped[Optional["Client"]] = relationship()
    device: Mapped[Optional["Device"]] = relationship()
    repair_history: Mapped[list["AssetRepairHistory"]] = relationship(back_populates="asset")


class Maintenance(Base):
    __tablename__ = "maintenance"

    id: Mapped[int] = mapped_column(primary_key=True)
    maintenance_number: Mapped[str] = mapped_column(String(24), unique=True)  # MNT-2026-000001
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assets.id"))
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"))
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    technician_id: Mapped[Optional[int]] = mapped_column(ForeignKey("technicians.id"))

    employee_name: Mapped[Optional[str]] = mapped_column(String(120))
    device_model: Mapped[Optional[str]] = mapped_column(String(150))
    issue: Mapped[Optional[str]] = mapped_column(Text)
    repair_details: Mapped[Optional[str]] = mapped_column(Text)
    cost: Mapped[Optional[float]]

    # Received | Assigned | In Repair | Completed | Returned | Closed | Overdue
    status: Mapped[str] = mapped_column(String(30), default="Received")

    gate_pass_number: Mapped[Optional[str]] = mapped_column(String(24))
    gate_pass_reason: Mapped[Optional[str]] = mapped_column(String(255))
    authorized_by: Mapped[Optional[str]] = mapped_column(String(120))
    actual_return_date: Mapped[Optional[dt.date]]
    invoice_number: Mapped[Optional[str]] = mapped_column(String(24))
    technician_shop: Mapped[Optional[str]] = mapped_column(String(120))
    technician_contact: Mapped[Optional[str]] = mapped_column(String(40))

    entry_date: Mapped[dt.date] = mapped_column(default=dt.date.today)
    expected_return_date: Mapped[Optional[dt.date]]
    completed_date: Mapped[Optional[dt.date]]

    warranty_months: Mapped[Optional[int]]
    warranty_until: Mapped[Optional[dt.date]]

    bill_image: Mapped[Optional[str]] = mapped_column(String(255))  # storage path/reference
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_completed: Mapped[bool] = mapped_column(default=False)

    asset: Mapped[Optional["Asset"]] = relationship()
    department: Mapped[Optional["Department"]] = relationship()
    category: Mapped[Optional["Category"]] = relationship()
    technician: Mapped[Optional["Technician"]] = relationship()


class AssetRepairHistory(Base):
    __tablename__ = "asset_repair_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"))
    repair_date: Mapped[dt.date] = mapped_column(default=dt.date.today)
    issue: Mapped[Optional[str]] = mapped_column(Text)
    repair_details: Mapped[Optional[str]] = mapped_column(Text)
    cost: Mapped[Optional[float]]
    technician_id: Mapped[Optional[int]] = mapped_column(ForeignKey("technicians.id"))
    status: Mapped[Optional[str]] = mapped_column(String(30))

    asset: Mapped["Asset"] = relationship(back_populates="repair_history")
    technician: Mapped[Optional["Technician"]] = relationship()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    # Administrator | IT Manager | IT Technician | Viewer  (full granular
    # role/permission tables are a Phase 8 item per the brief's own roadmap)
    role: Mapped[str] = mapped_column(String(30), default="Viewer")
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[Optional[dt.datetime]]


# ---- NEW tables the brief asks for but that did not exist originally ----

class AuditLog(Base):
    """NEW — spec section 32."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(40))  # Create/Update/Delete/Login/...
    entity: Mapped[str] = mapped_column(String(60))
    record_id: Mapped[Optional[int]]
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
    computer_name: Mapped[Optional[str]] = mapped_column(String(120))


class AppSetting(Base):
    """NEW — spec section 46/62. Simple key/value app settings store."""
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True)
    value: Mapped[Optional[str]] = mapped_column(String(255))


class NumberSequence(Base):
    """NEW — replaces/unifies gate_pass_sequence, gp_sequence and
    invoice_sequence with one concurrency-safe counter per prefix+year,
    also covers AST- and MNT- numbers (spec section 50)."""
    __tablename__ = "number_sequences"
    __table_args__ = (UniqueConstraint("prefix", "year", name="uq_prefix_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    prefix: Mapped[str] = mapped_column(String(10))
    year: Mapped[int] = mapped_column()
    last_value: Mapped[int] = mapped_column(default=0)
