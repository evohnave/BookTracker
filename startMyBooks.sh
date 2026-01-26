#!/usr/bin/env bash
set -euo pipefail      # -e exit on error, -u error on unset vars, -o pipefail catch pipeline errors

# Enable case-insensitive pattern matching (for *mybooks* style checks)
shopt -s nocasematch

# ────────────────────────────────────────────────
# Check virtual environment
# ────────────────────────────────────────────────
if [[ -z "${VIRTUAL_ENV:-}" ]] || [[ "$VIRTUAL_ENV" != *mybooks* && "$VIRTUAL_ENV" != *booktracker* ]]; then
    cat >&2 <<'EOF'
Error: This script must be run inside the correct virtual environment.

Expected: VIRTUAL_ENV path contains 'mybooks' or 'booktracker' (case-insensitive)

Current value:
  VIRTUAL_ENV = ${VIRTUAL_ENV:-not activated}

Quick fix (common locations):
  source .venv/bin/activate           # most Linux/macOS setups
  # or
  source .venv/Scripts/activate       # Windows (Git Bash, WSL, etc.)
  # or
  source ~/venvs/mybooks/bin/activate
EOF
    exit 1
fi

# Turn off case-insensitivity after the check
shopt -u nocasematch

# Make sure python is inside VIRTUAL_ENV somewhere
if [[ "$(command -v python)" != *"${VIRTUAL_ENV}"* ]]; then
    echo "Warning: python not inside VIRTUAL_ENV → possible wrong interpreter" >&2
fi

# ────────────────────────────────────────────────
# Start the app
# ────────────────────────────────────────────────

echo "Starting Uvicorn in venv: $(basename "${VIRTUAL_ENV}")"
echo "Python : $(python -c 'import sys; print(sys.version.split()[0])')"
echo "Running: uv run uvicorn main:app --reload"

# Run in background so script can exit cleanly (or remove & to keep it foreground)
uv run uvicorn main:app --reload &
