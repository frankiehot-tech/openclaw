#!/usr/bin/env zsh
set -euo pipefail

ROOT="${ATHENA_RUNTIME_ROOT:-/Volumes/1TB-M2/openclaw}"
PYTHON="${PYTHON:-/opt/homebrew/bin/python3}"

cd "$ROOT"

echo "=== M4 Best State Profile ==="
echo "Running snapshot collection..."
echo

"$PYTHON" "$ROOT/scripts/m4_best_state_profile.py" 2>&1

echo
echo "=== End of profile ==="