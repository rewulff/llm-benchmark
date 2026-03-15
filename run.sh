#!/usr/bin/env bash
# LLM Benchmark Runner
# Stellt sicher dass smolagents + litellm verfuegbar sind, dann startet run_benchmark.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"

# venv erstellen falls noetig
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating venv..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install -q 'smolagents[litellm]'
fi

# Aktivieren und ausfuehren
exec "$VENV_DIR/bin/python3" "$SCRIPT_DIR/run_benchmark.py" "$@"
