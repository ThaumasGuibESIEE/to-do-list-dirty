#!/usr/bin/env python
"""Render a concise test status report from test_list.yaml and result_test_auto.json."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "test_list.yaml"
RESULT_PATH = ROOT / "result_test_auto.json"


def load_plan():
    if not PLAN_PATH.exists():
        raise SystemExit(f"Fichier introuvable: {PLAN_PATH}")

    tests = []
    for line in PLAN_PATH.read_text(encoding="utf-8").splitlines():
        match = re.search(r"\b(T[AM]\d+)\b", line, flags=re.IGNORECASE)
        if not match:
            continue
        raw_id = match.group(1).upper()
        tests.append(
            {
                "id": raw_id,
                "type": "auto" if raw_id.startswith("TA") else "manual",
            }
        )
    return tests


def load_results():
    if not RESULT_PATH.exists():
        return {}
    data = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    results = {}
    for entry in data.get("tests", []):
        key = (entry.get("id") or entry.get("test", "")).upper()
        if not key:
            continue
        results[key] = entry.get("status")
    return results


def main():
    print("Lecture des tests auto via result_test_auto.json…")
    if RESULT_PATH.exists():
        print("OK")
    else:
        print("Fichier introuvable, les tests auto n'ont pas encore été exécutés.")

    plan = load_plan()
    results = load_results()

    passed = failed = not_found = manual = skipped = 0

    for test in plan:
        status = results.get(test["id"])
        if test["type"] == "manual":
            label = "🫱Manual test needed"
            manual += 1
        else:
            if status == "passed":
                label = "✅Passed"
                passed += 1
            elif status in {"failed", "error"}:
                label = "❌Failed"
                failed += 1
            elif status == "skipped":
                label = "⚠️Skipped"
                skipped += 1
            else:
                label = "🕳Not found"
                not_found += 1
        print(f"{test['id']} | {test['type']} | {label}")

    total = len(plan)

    def pct(n: int) -> float:
        return (n / total * 100) if total else 0.0

    print()
    print(f"Number of tests: {total}")
    print(f"✅Passed tests: {passed} ({pct(passed):.1f}%)")
    print(f"❌Failed tests: {failed} ({pct(failed):.1f}%)")
    print(f"🕳Not found tests: {not_found} ({pct(not_found):.1f}%)")
    print(f"🫱Test to pass manually: {manual} ({pct(manual):.1f}%)")
    print(f"✅Passed + 🫱Manual: {passed + manual} ({pct(passed + manual):.1f}%)")


if __name__ == "__main__":
    main()
