-- =====================================================================
-- 002_new_tables.sql
--
-- Additive only — creates new tables, never renames or drops anything
-- that exists (spec section 2 & 62). Safe to run multiple times (each
-- CREATE is guarded). Run 001_review_existing_schema.sql first and
-- reconcile app/db/models.py against its output before relying on this
-- against production.
--
-- NOTE on gate_pass_sequence / gp_sequence / invoice_sequence: this
-- script does NOT touch those three existing tables. number_sequences
-- below is a new, separate counter used by app/services/numbering_service.py
-- for local development. Decide with whoever owns the database whether
-- to (a) migrate those three into number_sequences, (b) keep them and
-- point numbering_service.py at them instead, or (c) run both side by
-- side during a transition. That decision needs a human who knows what
-- else currently reads those three tables — this script deliberately
-- does not make it for you.
-- =====================================================================

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'audit_logs')
BEGIN
    CREATE TABLE audit_logs (
        id            INT IDENTITY(1,1) PRIMARY KEY,
        user_id       INT NULL,
        action        NVARCHAR(40) NOT NULL,
        entity        NVARCHAR(60) NOT NULL,
        record_id     INT NULL,
        old_value     NVARCHAR(MAX) NULL,
        new_value     NVARCHAR(MAX) NULL,
        [timestamp]   DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        computer_name NVARCHAR(120) NULL,
        CONSTRAINT FK_audit_logs_users FOREIGN KEY (user_id) REFERENCES users(id)
    );
    CREATE INDEX IX_audit_logs_entity_record ON audit_logs(entity, record_id);
    CREATE INDEX IX_audit_logs_timestamp ON audit_logs([timestamp]);
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'app_settings')
BEGIN
    CREATE TABLE app_settings (
        id    INT IDENTITY(1,1) PRIMARY KEY,
        [key] NVARCHAR(80) NOT NULL UNIQUE,
        value NVARCHAR(255) NULL
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'number_sequences')
BEGIN
    CREATE TABLE number_sequences (
        id         INT IDENTITY(1,1) PRIMARY KEY,
        prefix     NVARCHAR(10) NOT NULL,
        [year]     INT NOT NULL,          -- 0 = not year-scoped; YYYYMM for invoice's monthly scope
        last_value INT NOT NULL DEFAULT 0,
        CONSTRAINT UQ_number_sequences_prefix_year UNIQUE (prefix, [year])
    );
END
GO

-- Note on "ODBC SQL type -16 is not yet supported" (spec section 35):
-- that error comes from a client-side tool's column-type mapping (SQL
-- type -16 = SQL_WLONGVARCHAR / NVARCHAR(MAX) under older ODBC drivers),
-- not database corruption. Practical fix on the app side is already in
-- place: SQLAlchemy's mssql+pyodbc dialect maps large text columns
-- correctly with a current "ODBC Driver 17/18 for SQL Server" — if a
-- separate analysis tool still throws it, that tool's own ODBC driver
-- needs updating, not the schema.

-- =====================================================================
-- Phase 5 additions: three Gate Pass fields (spec section 21 — Reason,
-- Authorized By, Actual Return Date) that the original `maintenance`
-- column list didn't include. Additive ALTER only, each guarded so this
-- is safe to run more than once. Existing rows get NULL in these three
-- columns until the app fills them in going forward.
-- =====================================================================

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'maintenance' AND COLUMN_NAME = 'gate_pass_reason'
)
BEGIN
    ALTER TABLE maintenance ADD gate_pass_reason NVARCHAR(255) NULL;
END
GO

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'maintenance' AND COLUMN_NAME = 'authorized_by'
)
BEGIN
    ALTER TABLE maintenance ADD authorized_by NVARCHAR(120) NULL;
END
GO

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'maintenance' AND COLUMN_NAME = 'actual_return_date'
)
BEGIN
    ALTER TABLE maintenance ADD actual_return_date DATE NULL;
END
GO

-- On maintenance_status_history (listed as a Phase-62 "potential
-- additional table"): deliberately not added. Every workflow transition
-- (spec section 17) is already written to audit_logs with
-- entity='Maintenance', so a second, narrower history table would just
-- duplicate it. The Maintenance detail screen's History tab reads from
-- audit_logs directly. Revisit only if audit_logs' generality becomes a
-- real reporting problem.
