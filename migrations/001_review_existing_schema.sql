-- =====================================================================
-- 001_review_existing_schema.sql
--
-- READ-ONLY. Makes no changes. Run this against the real Vgotel_IT_DB
-- first (SQL Server Management Studio, Azure Data Studio, or `sqlcmd`)
-- to list actual columns, types and foreign keys, so app/db/models.py
-- can be reconciled against reality rather than the brief's field list
-- (which names business fields like "Person" or "Floor", not
-- necessarily the real column names). See scripts/introspect_mssql_schema.py
-- for a Python version of the same check that writes the result to JSON.
-- =====================================================================

SELECT
    t.name  AS table_name,
    c.name  AS column_name,
    ty.name AS data_type,
    c.max_length,
    c.is_nullable,
    c.is_identity
FROM sys.tables t
JOIN sys.columns c ON c.object_id = t.object_id
JOIN sys.types  ty ON ty.user_type_id = c.user_type_id
WHERE t.name IN (
    'asset_repair_history', 'assets', 'categories', 'clients', 'departments',
    'devices', 'gate_pass_sequence', 'gp_sequence', 'invoice_sequence',
    'maintenance', 'technicians', 'users'
)
ORDER BY t.name, c.column_id;

-- Existing foreign keys (compare against the three the brief lists:
-- clients.department_id -> departments.id,
-- devices.department_id -> departments.id,
-- asset_repair_history.asset_id -> assets.id)
SELECT
    fk.name AS constraint_name,
    tp.name AS parent_table,
    cp.name AS parent_column,
    tr.name AS ref_table,
    cr.name AS ref_column
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.tables tp ON tp.object_id = fkc.parent_object_id
JOIN sys.columns cp ON cp.object_id = tp.object_id AND cp.column_id = fkc.parent_column_id
JOIN sys.tables tr ON tr.object_id = fkc.referenced_object_id
JOIN sys.columns cr ON cr.object_id = tr.object_id AND cr.column_id = fkc.referenced_column_id;

-- Existing indexes (spec section 34 — "do not blindly create duplicate
-- indexes"; check this before Phase 4+ adds any).
SELECT
    t.name AS table_name, i.name AS index_name, i.type_desc,
    STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
FROM sys.indexes i
JOIN sys.tables t ON t.object_id = i.object_id
JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id
WHERE t.name IN (
    'asset_repair_history', 'assets', 'categories', 'clients', 'departments',
    'devices', 'gate_pass_sequence', 'gp_sequence', 'invoice_sequence',
    'maintenance', 'technicians', 'users'
)
GROUP BY t.name, i.name, i.type_desc
ORDER BY t.name;

-- Row counts, just to know the real scale before Phase 4 designs pagination.
SELECT 'assets' AS tbl, COUNT(*) AS row_count FROM assets
UNION ALL SELECT 'maintenance', COUNT(*) FROM maintenance
UNION ALL SELECT 'devices', COUNT(*) FROM devices
UNION ALL SELECT 'clients', COUNT(*) FROM clients
UNION ALL SELECT 'asset_repair_history', COUNT(*) FROM asset_repair_history;
