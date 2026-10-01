"""
Concurrency-safe business-number generation.

Uses one `number_sequences` table (prefix, year) with an atomic
UPDATE ... RETURNING so two users can never receive the same number
(spec section 50). This is a NEW table, added alongside — not instead
of — the existing gate_pass_sequence / gp_sequence / invoice_sequence
tables (spec section 2: "Do NOT randomly rename existing database
tables"). Recommendation for the real Vgotel_IT_DB: reconcile the three
legacy counters into this single table during the migration step in
migrations/002_new_tables.sql, after confirming with whoever owns the
database that nothing else still reads the legacy counters directly.

On SQL Server, `.returning()` compiles to an OUTPUT clause, which is
still atomic per-row — no extra locking hints are required for this
single-row-increment pattern.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import NumberSequence


def _increment(session: Session, prefix: str, scope_key: int) -> int:
    row = session.scalar(
        select(NumberSequence).where(
            NumberSequence.prefix == prefix, NumberSequence.year == scope_key
        )
    )
    if row is None:
        row = NumberSequence(prefix=prefix, year=scope_key, last_value=0)
        session.add(row)
        session.flush()

    stmt = (
        update(NumberSequence)
        .where(NumberSequence.id == row.id)
        .values(last_value=NumberSequence.last_value + 1)
        .returning(NumberSequence.last_value)
    )
    new_value = session.execute(stmt).scalar_one()
    session.commit()
    return new_value


def next_asset_number(session: Session, prefix: str) -> str:
    """Not year-scoped, e.g. AST-000001."""
    n = _increment(session, prefix, scope_key=0)
    return f"{prefix}-{n:06d}"


def next_maintenance_number(session: Session, prefix: str) -> str:
    """e.g. MNT-2026-000001."""
    year = dt.date.today().year
    n = _increment(session, prefix, scope_key=year)
    return f"{prefix}-{year}-{n:06d}"


def next_gate_pass_number(session: Session, prefix: str) -> str:
    """e.g. GP-2026-000001."""
    year = dt.date.today().year
    n = _increment(session, prefix, scope_key=year)
    return f"{prefix}-{year}-{n:06d}"


def next_invoice_number(session: Session, prefix: str) -> str:
    """e.g. INV-2026-09-0001 (month-scoped, per spec section 22)."""
    today = dt.date.today()
    scope_key = today.year * 100 + today.month
    n = _increment(session, prefix, scope_key=scope_key)
    return f"{prefix}-{today.year}-{today.month:02d}-{n:04d}"
