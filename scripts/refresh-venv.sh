#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Recreating virtual environment in $ROOT_DIR/.venv"
rm -rf .venv
python3 -m venv .venv

echo "Upgrading pip tooling"
.venv/bin/python -m pip install --upgrade pip setuptools wheel

echo "Installing latest resolvable dependencies"
.venv/bin/pip install --upgrade --upgrade-strategy eager -r requirements.txt

echo "Running smoke test"
.venv/bin/python auto-commit.py --help >/dev/null

echo "Virtual environment refreshed successfully"
