#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${A11Y_HOST:-127.0.0.1}"
PORT="${A11Y_PORT:-8000}"
BASE_URL="http://${HOST}:${PORT}"
RAW_A11Y_JSON="$ROOT_DIR/result_test_a11y_raw.json"
REPORT_JSON="$ROOT_DIR/result_test_a11y.json"

# Choose the python command (pipenv > local venv > system python)
PYTHON_CMD=(python)
if command -v pipenv >/dev/null 2>&1; then
  PYTHON_CMD=(pipenv run python)
fi
if [[ -x "$ROOT_DIR/.venv/Scripts/python.exe" ]]; then
  PYTHON_CMD=("$ROOT_DIR/.venv/Scripts/python.exe")
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_CMD=("$ROOT_DIR/.venv/bin/python")
fi

run_py() {
  "${PYTHON_CMD[@]}" "$@"
}

cd "$ROOT_DIR"

echo "Preparing database with fixtures..."
run_py manage.py migrate --noinput >/dev/null
run_py manage.py loaddata tasks/fixtures/dataset.json >/dev/null

LOG_FILE="$(mktemp 2>/dev/null || mktemp -t a11y-server)"
echo "Starting Django server for a11y checks (log: $LOG_FILE)..."
run_py manage.py runserver "${HOST}:${PORT}" --noreload --insecure >"$LOG_FILE" 2>&1 &
SERVER_PID=$!

cleanup() {
  if kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    kill "$SERVER_PID"
  fi
}
trap cleanup EXIT

echo "Waiting for server on ${BASE_URL}..."
python - "$HOST" "$PORT" <<'PY'
import socket, sys, time

host, port = sys.argv[1], int(sys.argv[2])
deadline = time.time() + 30
while time.time() < deadline:
    with socket.socket() as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
        except OSError:
            time.sleep(0.5)
            continue
        else:
            sys.exit(0)
sys.exit("Server not responding on {}:{}".format(host, port))
PY

if [[ ! -d "$ROOT_DIR/node_modules/pa11y-ci" ]]; then
  echo "Installing pa11y-ci (node_modules missing)..."
  npm install --no-progress --no-fund
fi

PA11Y_CONFIG="$(mktemp 2>/dev/null || mktemp -t pa11y-config)"
cat >"$PA11Y_CONFIG" <<EOF
{
  "defaults": {
    "standard": "WCAG2A",
    "timeout": 60000,
    "wait": 800,
    "chromeLaunchConfig": {
      "args": ["--no-sandbox", "--disable-dev-shm-usage", "--headless=new"]
    }
  },
  "urls": [
    "${BASE_URL}/",
    "${BASE_URL}/update_task/1",
    "${BASE_URL}/delete/1"
  ]
}
EOF

echo "Running pa11y-ci against ${BASE_URL}..."
npx pa11y-ci --config "$PA11Y_CONFIG" --reporter json >"$RAW_A11Y_JSON"

python - "$RAW_A11Y_JSON" "$REPORT_JSON" <<'PY'
import json
import sys
from pathlib import Path

raw_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])

if not raw_path.exists():
    sys.exit("Pa11y raw report not found")

# pa11y-ci JSON can be either a list (array of runs) or an object with results.
data = json.loads(raw_path.read_text(encoding="utf-8"))

def count_issues(payload):
    # Newer pa11y-ci versions: {"total":3,"passes":3,"errors":0,"results":{url: [issues]}}
    if isinstance(payload, dict) and "results" in payload:
        return sum(len(v) for v in payload.get("results", {}).values())
    # Legacy format: list of entries each with "issues"
    if isinstance(payload, list):
        return sum(len(entry.get("issues", [])) for entry in payload)
    return 0

issues = count_issues(data)
status = "passed" if issues == 0 else "failed"
payload = {
    "tests": [
        {
            "id": "TA16",
            "name": "Audit accessibilite WCAG 2.1 A",
            "status": status,
            "details": {"issues": issues},
        }
    ]
}
out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

if status != "passed":
    sys.exit(f"A11y issues found: {issues}")
else:
    print(f"A11y test passed (0 issues) -> {out_path}")
PY
