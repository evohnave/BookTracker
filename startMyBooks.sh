#!/usr/bin/env bash

set -ueo pipefail

if [[ "$VIRTUAL_ENV" !=  "(mybooks)" ]]; then
  echo "Please activate the virtual environment"
  echo "source .venv/Scripts/activate"
  exit 1
fi

uv run uvicorn main:app --reload
