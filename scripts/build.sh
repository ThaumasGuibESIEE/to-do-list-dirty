#!/usr/bin/env bash
set -euo pipefail

# Usage: ./build.sh version=1.0.1
arg="${1:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ "$arg" == version=* ]]; then
  VERSION="${arg#version=}"
else
  echo "Usage: ./build.sh version=x.y.z" >&2
  exit 1
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Version '$VERSION' invalide (attendu x.y.z)" >&2
  exit 1
fi

SETTINGS_PATH="todo/settings.py"

if [[ ! -f "$SETTINGS_PATH" ]]; then
  echo "Fichier introuvable: $SETTINGS_PATH" >&2
  exit 1
fi

echo "Vérification du lint (Ruff)..."
if command -v pipenv >/dev/null 2>&1; then
  pipenv run ruff check .
elif [[ -x ".venv/bin/ruff" ]]; then
  .venv/bin/ruff check .
elif [[ -x ".venv/Scripts/ruff.exe" ]]; then
  .venv/Scripts/ruff.exe check .
else
  echo "Ruff introuvable. Installez les dépendances (pipenv install) avant de lancer le build." >&2
  exit 1
fi

echo "Exécution de la matrice de tests..."
if [[ -x "$SCRIPT_DIR/test_matrix.sh" ]]; then
  bash "$SCRIPT_DIR/test_matrix.sh"
else
  echo "scripts/test_matrix.sh introuvable ou non exécutable" >&2
  exit 1
fi

if git tag --list "$VERSION" | grep -q .; then
  echo "Le tag '$VERSION' existe déjà" >&2
  exit 1
fi

# Met à jour la variable VERSION dans settings.py
python - <<PY
from pathlib import Path
import re, sys

version = "$VERSION"
path = Path("$SETTINGS_PATH")
text = path.read_text()
new_text, count = re.subn(r"VERSION\s*=\s*['\"]([^'\"]*)['\"]", f"VERSION = '{version}'", text, count=1)
if count == 0:
    sys.exit("Aucune assignation VERSION trouvée")
path.write_text(new_text)
PY

echo "Ajout de toutes les modifications au commit..."
git add -A
git commit -m "Bump version to $VERSION"
git tag -a "$VERSION" -m "Version $VERSION"

ARCHIVE_NAME="todolist-$VERSION.zip"
git archive --format=zip --output "$ARCHIVE_NAME" --prefix="todolist-$VERSION/" HEAD

echo "Version $VERSION créée :"
echo " - settings mis à jour et commit"
echo " - tag '$VERSION' créé"
echo " - archive générée : $ARCHIVE_NAME"
