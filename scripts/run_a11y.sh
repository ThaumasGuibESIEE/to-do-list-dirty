#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${A11Y_HOST:-127.0.0.1}"
PORT="${A11Y_PORT:-8000}"
BASE_URL="http://${HOST}:${PORT}"

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

echo "Running pa11y-ci against ${BASE_URL}..."
npx pa11y-ci
