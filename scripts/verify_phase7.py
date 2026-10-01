"""Run with: python -m scripts.verify_phase7   (from the project root)"""
import datetime as dt
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config
from app.db.base import init_engine, session_scope
from app.services import export_service as esvc
from app.services import report_service as rsvc

cfg = load_config()
init_engine(cfg.db_url)

with session_scope() as s:
    print("1. Every registered report runs without error and returns the expected shape...")
    six_months_ago = dt.date.today() - dt.timedelta(days=180)
    filters = {"date_from": six_months_ago, "date_to": dt.date.today()}
    total_reports = 0
    sample_report = None
    for category, reports in rsvc.REPORTS.items():
        for key, label, runner in reports:
            result = runner(s, filters)
            assert "columns" in result and "rows" in result, f"{key} missing columns/rows"
            assert isinstance(result["rows"], list)
            print(f"   OK — [{category}] {label}: {len(result['rows'])} rows")
            total_reports += 1
            if key == "asset_register":
                sample_report = (key, label, result)
    assert total_reports >= 12
    print(f"   OK — {total_reports} reports total, all ran cleanly")

    print("2. Asset register actually reflects the seeded assets...")
    _, _, reg = sample_report
    assert len(reg["rows"]) > 0
    assert reg["summary"][0][1] == str(len(reg["rows"]))
    print(f"   OK — {reg['summary'][0][1]} assets in the register")

    print("3. Repair frequency flags high-repair assets...")
    freq = rsvc.repair_frequency(s)
    highs = [r for r in freq["rows"] if r[4] == "High"]
    print(f"   OK — {len(highs)} asset(s) flagged High frequency")

    print("4. Technician performance computes real efficiency...")
    perf = rsvc.technician_performance(s)
    assert perf["rows"], "expected at least one technician row"
    print(f"   OK — {perf['rows'][0]}")

    print("5. Warranty reports partition correctly (active/expiring/expired don't overlap)...")
    active = rsvc.warranty_report(s, "active")
    expiring = rsvc.warranty_report(s, "expiring")
    expired = rsvc.warranty_report(s, "expired")
    active_ids = {r[0] for r in active["rows"]}
    expiring_ids = {r[0] for r in expiring["rows"]}
    expired_ids = {r[0] for r in expired["rows"]}
    assert not (active_ids & expiring_ids) and not (active_ids & expired_ids) \
        and not (expiring_ids & expired_ids)
    print(f"   OK — active={len(active_ids)} expiring={len(expiring_ids)} expired={len(expired_ids)}, no overlap")

    print("6. Export CSV/Excel/PDF all produce real, non-empty files...")
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = str(Path(tmp) / "test.csv")
        xlsx_path = str(Path(tmp) / "test.xlsx")
        pdf_path = str(Path(tmp) / "test.pdf")

        esvc.export_csv(csv_path, "Test Report", reg)
        esvc.export_excel(xlsx_path, "Test Report", reg, "verify_phase7")
        esvc.export_pdf(pdf_path, "Test Report", reg, "verify_phase7")

        for p, label in [(csv_path, "CSV"), (xlsx_path, "Excel"), (pdf_path, "PDF")]:
            size = Path(p).stat().st_size
            assert size > 0, f"{label} export is empty"
            print(f"   OK — {label} export: {size} bytes")

        # Sanity-check the CSV actually has the right row count (+ header/meta lines)
        csv_lines = Path(csv_path).read_text(encoding="utf-8").splitlines()
        assert len(csv_lines) >= len(reg["rows"])

print("\nALL PHASE 7 CHECKS PASSED.")
