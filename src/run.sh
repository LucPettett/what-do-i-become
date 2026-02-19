#!/usr/bin/env bash
# Wrapper script: load src/.env then run the agent.

set -euo pipefail

FRAMEWORK_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$FRAMEWORK_DIR"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

exec python3 agent.py
