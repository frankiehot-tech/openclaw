#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
VENV_DIR="$ROOT/.venvs/athena-observability"
REQ_FILE="$ROOT/observability/requirements.txt"

mkdir -p "$ROOT/.venvs"

/opt/homebrew/bin/python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$REQ_FILE"

echo "Athena observability venv ready: $VENV_DIR"
