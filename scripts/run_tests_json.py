#!/usr/bin/env python
"""Execute Django tests and export a JSON report to result_test_auto.json."""

import json
import os
import sys
import unittest
from pathlib import Path

import django
from django.test.runner import DiscoverRunner

ROOT = Path(__file__).resolve().parent.parent
RESULT_PATH = ROOT / "result_test_auto.json"


def _test_node_id(test: unittest.TestCase) -> str:
    method = getattr(test, "_testMethodName", str(test))
    return (
        f"{test.__class__.__module__}."
        f"{test.__class__.__qualname__}."
        f"{method}"
    )


def _case_id_for(test: unittest.TestCase) -> str | None:
    method_name = getattr(test, "_testMethodName", None)
    if not method_name:
        return None
    method = getattr(test, method_name, None)
    return getattr(method, "test_case_id", None)


class JSONTestResult(unittest.TextTestResult):
    """Collect per-test results so we can write them to JSON."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases: list[dict[str, str]] = []

    def _record(self, test: unittest.TestCase, status: str, err=None) -> None:
        node_id = _test_node_id(test)
        entry = {
            "test": node_id,
            "status": status,
        }
        case_id = _case_id_for(test)
        if case_id:
            entry["id"] = case_id
        if err is not None:
            if isinstance(err, tuple):
                entry["message"] = self._exc_info_to_string(err, test)
            else:
                entry["message"] = str(err)
        self.cases.append(entry)

    def addSuccess(self, test):  # noqa: N802
        super().addSuccess(test)
        self._record(test, "passed")

    def addFailure(self, test, err):  # noqa: N802
        super().addFailure(test, err)
        self._record(test, "failed", err)

    def addError(self, test, err):  # noqa: N802
        super().addError(test, err)
        self._record(test, "error", err)

    def addSkip(self, test, reason):  # noqa: N802
        super().addSkip(test, reason)
        self._record(test, "skipped", reason)


class JSONTextTestRunner(unittest.TextTestRunner):
    resultclass = JSONTestResult


class JSONDiscoverRunner(DiscoverRunner):
    """Django test runner that keeps the JSON result object around."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("test_runner", JSONTextTestRunner)
        super().__init__(*args, **kwargs)
        self.json_result: JSONTestResult | None = None

    def run_suite(self, suite, **kwargs):
        runner = JSONTextTestRunner(
            verbosity=self.verbosity,
            failfast=self.failfast,
            buffer=self.buffer,
            resultclass=JSONTestResult,
        )
        self.json_result = runner.run(suite)
        return self.json_result


def write_json(result: JSONTestResult) -> None:
    payload = {
        "tests": result.cases,
        "summary": {
            "run": result.testsRun,
            "failed": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
        },
    }
    RESULT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"JSON des tests écrit dans {RESULT_PATH}")


def main(argv: list[str]) -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "todo.settings")
    sys.path.insert(0, str(ROOT))
    django.setup()

    runner = JSONDiscoverRunner(verbosity=1)

    failures = runner.run_tests(argv or None)
    if runner.json_result:
        write_json(runner.json_result)
    else:
        print("Aucun résultat JSON collecté.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
