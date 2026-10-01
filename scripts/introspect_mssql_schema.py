"""
Run this from a machine that can actually reach the real SQL Server
(this sandbox cannot — it has no network path to a private company
database). It only reads metadata (sys.tables/sys.columns), never data.

Usage:
    pip install pyodbc
    python introspect_mssql_schema.py --server YOUR_SERVER --database Vgotel_IT_DB

Writes schema_dump.json next to this script. Compare it against
app/db/models.py and adjust the ORM models to match reality before
pointing the app at production (see README.md).
"""
import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", default="Vgotel_IT_DB")
    parser.add_argument("--driver", default="ODBC Driver 17 for SQL Server")
    parser.add_argument("--trusted", action="store_true", default=True,
                         help="Use Windows/trusted authentication (default).")
    parser.add_argument("--username")
    parser.add_argument("--password")
    args = parser.parse_args()

    try:
        import pyodbc
    except ImportError:
        print("pyodbc is not installed. Run: pip install pyodbc", file=sys.stderr)
        sys.exit(1)

    if args.username:
        conn_str = (
            f"DRIVER={{{args.driver}}};SERVER={args.server};DATABASE={args.database};"
            f"UID={args.username};PWD={args.password}"
        )
    else:
        conn_str = (
            f"DRIVER={{{args.driver}}};SERVER={args.server};DATABASE={args.database};"
            f"Trusted_Connection=yes"
        )

    tables_of_interest = [
        "asset_repair_history", "assets", "categories", "clients", "departments",
        "devices", "gate_pass_sequence", "gp_sequence", "invoice_sequence",
        "maintenance", "technicians", "users",
    ]

    with pyodbc.connect(conn_str, timeout=10) as conn:
        cur = conn.cursor()
        result = {}
        for table in tables_of_interest:
            cur.execute(
                """
                SELECT c.name, ty.name, c.max_length, c.is_nullable, c.is_identity
                FROM sys.tables t
                JOIN sys.columns c ON c.object_id = t.object_id
                JOIN sys.types ty ON ty.user_type_id = c.user_type_id
                WHERE t.name = ?
                ORDER BY c.column_id
                """,
                table,
            )
            rows = cur.fetchall()
            if not rows:
                result[table] = {"exists": False}
                continue
            result[table] = {
                "exists": True,
                "columns": [
                    {
                        "name": r[0], "type": r[1], "max_length": r[2],
                        "nullable": bool(r[3]), "identity": bool(r[4]),
                    }
                    for r in rows
                ],
            }

    with open("schema_dump.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("Wrote schema_dump.json")
    for table, info in result.items():
        status = f"{len(info['columns'])} columns" if info["exists"] else "NOT FOUND"
        print(f"  {table}: {status}")


if __name__ == "__main__":
    main()
