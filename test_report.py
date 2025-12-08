#!/usr/bin/env python
"""Render a concise test status report from test_list.yaml and JSON results."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "test_list.yaml"
RESULT_PATH = ROOT / "result_test_auto.json"
SELENIUM_RESULT_PATH = ROOT / "result_test_selenium.json"
A11Y_RESULT_PATH = ROOT / "result_test_a11y.json"


def load_plan() -> list[dict[str, str]]:
    if not PLAN_PATH.exists():
        raise SystemExit(f"Fichier introuvable: {PLAN_PATH}")

    tests: list[dict[str, str]] = []
    for line in PLAN_PATH.read_text(encoding="utf-8").splitlines():
        match = re.search(r"\b(T[A-Z]+\d+)\b", line, flags=re.IGNORECASE)
        if not match:
            continue
        raw_id = match.group(1).upper()
        upper_line = line.upper()
        if "[AUTO-SELENIUM" in upper_line:
            test_type = "auto-selenium"
        elif "[AUTO-A11Y" in upper_line:
            test_type = "auto-a11y"
        elif "[AUTO" in upper_line:
            test_type = "auto"
        else:
            test_type = "manual"
        tests.append(
            {
                "id": raw_id,
                "type": test_type,
            }
        )
    return tests


def load_results(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    results: dict[str, str] = {}
    for entry in data.get("tests", []):
        key = (entry.get("id") or entry.get("test", "")).upper()
        if not key:
            continue
        results[key] = entry.get("status")
    return results


def main() -> None:
    print("Lecture des tests auto via result_test_auto.json...")
    print(
        "OK"
        if RESULT_PATH.exists()
        else "Fichier introuvable, tests auto non exécutés."
    )

    print("Lecture des tests Selenium via result_test_selenium.json...")
    print(
        "OK"
        if SELENIUM_RESULT_PATH.exists()
        else "Fichier introuvable pour Selenium."
    )

    print("Lecture des tests accessibilité via result_test_a11y.json...")
    print(
        "OK"
        if A11Y_RESULT_PATH.exists()
        else "Fichier introuvable pour l'accessibilité."
    )

    plan = load_plan()
    unit_results = load_results(RESULT_PATH)
    selenium_results = load_results(SELENIUM_RESULT_PATH)
    a11y_results = load_results(A11Y_RESULT_PATH)

    passed = failed = not_found = manual = skipped = 0

    for test in plan:
        if test["type"] == "auto-selenium":
            status = selenium_results.get(test["id"])
        elif test["type"] == "auto-a11y":
            status = a11y_results.get(test["id"])
        else:
            status = unit_results.get(test["id"])

        if test["type"] == "manual":
            label = "[MANUAL] Manual test needed"
            manual += 1
        else:
            if status == "passed":
                label = "[PASS] Passed"
                passed += 1
            elif status in {"failed", "error"}:
                label = "[FAIL] Failed"
                failed += 1
            elif status == "skipped":
                label = "[SKIP] Skipped"
                skipped += 1
            else:
                label = "[MISSING] Not found"
                not_found += 1
        print(f"{test['id']} | {test['type']} | {label}")

    total = len(plan)

    def pct(n: int) -> float:
        return (n / total * 100) if total else 0.0

    print()
    print(f"Number of tests: {total}")
    print(f"Passed tests: {passed} ({pct(passed):.1f}%)")
    print(f"Failed tests: {failed} ({pct(failed):.1f}%)")
    print(f"Not found tests: {not_found} ({pct(not_found):.1f}%)")
    print(f"Manual tests to do: {manual} ({pct(manual):.1f}%)")
    print(f"Passed + Manual: {passed + manual} ({pct(passed + manual):.1f}%)")


if __name__ == "__main__":
    main()
