#!/usr/bin/env python
"""Generate a delivery PDF listing tests and their status with timestamp."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
PLAN_PATH = ROOT / "test_list.yaml"
UNIT_JSON = ROOT / "result_test_auto.json"
SELENIUM_JSON = ROOT / "result_test_selenium.json"
A11Y_JSON = ROOT / "result_test_a11y.json"


def load_plan() -> List[Tuple[str, str]]:
    """Return list of (id, type) where type in auto/auto-selenium/auto-a11y/manual."""
    tests: List[Tuple[str, str]] = []
    for line in PLAN_PATH.read_text(encoding="utf-8").splitlines():
        if "TA" not in line and "TM" not in line:
            continue
        parts = line.split()
        if not parts:
            continue
        raw_id = ""
        for p in parts:
            if p.upper().startswith(("TA", "TM")):
                raw_id = "".join(ch for ch in p if ch.isalnum()).upper()
                break
        if not raw_id:
            continue
        upper_line = line.upper()
        if "[AUTO-SELENIUM" in upper_line:
            test_type = "auto-selenium"
        elif "[AUTO-A11Y" in upper_line:
            test_type = "auto-a11y"
        elif "[AUTO" in upper_line:
            test_type = "auto"
        else:
            test_type = "manual"
        tests.append((raw_id, test_type))
    return tests


def load_results(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    res: Dict[str, str] = {}
    for entry in data.get("tests", []):
        key = (entry.get("id") or entry.get("test", "")).upper()
        if key:
            res[key] = entry.get("status", "")
    return res


def build_rows() -> List[Tuple[str, str]]:
    """Return rows [(id, status_label)]."""
    plan = load_plan()
    unit = load_results(UNIT_JSON)
    sel = load_results(SELENIUM_JSON)
    a11y = load_results(A11Y_JSON)

    rows: List[Tuple[str, str]] = []
    for test_id, ttype in plan:
        if ttype == "auto-selenium":
            status = sel.get(test_id, "missing")
        elif ttype == "auto-a11y":
            status = a11y.get(test_id, "missing")
        elif ttype == "auto":
            status = unit.get(test_id, "missing")
        else:
            status = "manual"
        rows.append((test_id, status))
    return rows


def render_pdf(rows: List[Tuple[str, str]], output_path: Path) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Bon de livraison - Tests", ln=True, align="C")

    pdf.set_font("Arial", size=12)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    pdf.cell(0, 10, f"Horodatage: {ts}", ln=True)
    pdf.ln(4)
    pdf.cell(0, 10, "Liste des tests:", ln=True)

    pdf.set_font("Arial", size=11)
    for test_id, status in rows:
        label = status
        if status == "passed":
            label = "passed"
        elif status in {"failed", "error"}:
            label = "failed"
        elif status == "skipped":
            label = "skipped"
        elif status == "manual":
            label = "manual (à réaliser)"
        elif status == "missing":
            label = "absent des rapports"
        pdf.cell(0, 8, f"- {test_id}: {label}", ln=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate delivery PDF for test results.")
    parser.add_argument(
        "--output",
        default=str(ROOT / "delivery_note.pdf"),
        help="Output PDF path",
    )
    args = parser.parse_args()
    rows = build_rows()
    render_pdf(rows, Path(args.output))
    print(f"PDF generated at {args.output}")


if __name__ == "__main__":
    main()
