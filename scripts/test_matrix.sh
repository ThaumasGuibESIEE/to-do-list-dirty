#!/usr/bin/env bash
set -euo pipefail

# Run the Django test suite against a matrix of Python and Django versions.
# Uses pipenv with a temporary Pipfile/venv per combo to avoid touching the main env.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_VERSIONS=("3.13" "3.12" "3.9" "2.7")
DJANGO_SPECS=("==5.*" "==4.*")

declare -a PIPENV_CMD

find_pipenv() {
  if command -v pipenv >/dev/null 2>&1; then
    PIPENV_CMD=(pipenv)
    return 0
  fi

  if command -v py >/dev/null 2>&1; then
    for ver in 3.13 3.12  3.9; do
      if py "-$ver" -m pipenv --version >/dev/null 2>&1; then
        PIPENV_CMD=(py "-$ver" -m pipenv)
        return 0
      fi
    done
  fi

  if command -v python >/dev/null 2>&1 && python -m pipenv --version >/dev/null 2>&1; then
    PIPENV_CMD=(python -m pipenv)
    return 0
  fi

  return 1
}

if ! find_pipenv; then
  echo "pipenv introuvable. Installez-le, par exemple :" >&2
  echo "  py -3.12 -m pip install --user pipenv" >&2
  echo "Puis relancez le script." >&2
  exit 1
fi

find_python_path() {
  local ver="$1"
  if command -v py >/dev/null 2>&1; then
    if py "-$ver" -c "import sys; print(sys.executable)" >/dev/null 2>&1; then
      py "-$ver" -c "import sys; print(sys.executable)"
      return 0
    fi
  fi
  if command -v "python$ver" >/dev/null 2>&1; then
    command -v "python$ver"
    return 0
  fi
  return 1
}

python_version_tuple() {
  local py_cmd="$1"
  "$py_cmd" - <<'PY'
import sys
print("{} {}".format(sys.version_info.major, sys.version_info.minor))
PY
}

is_supported_combo() {
  local py_major="$1"
  local py_minor="$2"
  local spec="$3"
  # Python 2.x is not supported by this project
  if [[ "$py_major" -lt 3 ]]; then
    return 1
  fi
  # Django 5 requires Python >= 3.10
  if [[ "$spec" == "==5.*" && ( "$py_major" -lt 3 || "$py_minor" -lt 10 ) ]]; then
    return 1
  fi
  # Django 4 requires Python >= 3.8
  if [[ "$spec" == "==4.*" && ( "$py_major" -lt 3 || "$py_minor" -lt 8 ) ]]; then
    return 1
  fi
  # Django 3 requires Python >= 3.6
  if [[ "$spec" == "==3.*" && ( "$py_major" -lt 3 || "$py_minor" -lt 6 ) ]]; then
    return 1
  fi
  return 0
}

install_with_retry() {
  local pipfile="$1"
  local py_path="$2"
  local max_attempts=3
  local attempt=1
  while (( attempt <= max_attempts )); do
    if PIPENV_PIPFILE="$pipfile" PIPENV_VENV_IN_PROJECT=1 "${PIPENV_CMD[@]}" --python "$py_path" install --deploy --skip-lock >/dev/null; then
      return 0
    fi
    echo "Install failed (attempt ${attempt}/${max_attempts}), retrying..." >&2
    sleep 3
    attempt=$((attempt + 1))
  done
  return 1
}

run_combo() {
  local py_ver="$1"
  local django_spec="$2"

  local py_path
  if ! py_path="$(find_python_path "$py_ver")"; then
    echo "Skipping Python $py_ver: interpreter not found."
    return 0
  fi

  local py_major py_minor
  read -r py_major py_minor <<<"$(python_version_tuple "$py_path")"

  if ! is_supported_combo "$py_major" "$py_minor" "$django_spec"; then
    echo "Skipping combo: Python ${py_major}.${py_minor} with Django $django_spec is unsupported."
    return 0
  fi

  echo
  echo "=== Python ${py_major}.${py_minor} + Django $django_spec ==="

  local tmpdir
  tmpdir="$(mktemp -d)"

  cat >"$tmpdir/Pipfile" <<EOF
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
django = "${django_spec}"

[dev-packages]

[requires]
python_version = "${py_ver}"
EOF

  if ! install_with_retry "$tmpdir/Pipfile" "$py_path"; then
    echo "Skipping combo: installation failed after retries." >&2
    rm -rf "$tmpdir"
    return 0
  fi

  PIPENV_PIPFILE="$tmpdir/Pipfile" PIPENV_VENV_IN_PROJECT=1 "${PIPENV_CMD[@]}" run python "$ROOT_DIR/manage.py" test

  echo "OK: Python ${py_major}.${py_minor} + Django ${django_spec}"

  rm -rf "$tmpdir"
}

for py_ver in "${PYTHON_VERSIONS[@]}"; do
  for django_spec in "${DJANGO_SPECS[@]}"; do
    run_combo "$py_ver" "$django_spec"
  done
done
