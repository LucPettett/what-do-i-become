#!/usr/bin/env bash
# Wrapper script — sources .env and runs the agent.
# Usage:
#   ./run.sh            (manual run, output to terminal)
#   cron: ./run.sh >> cron.log 2>&1

set -e
cd "$(dirname "$0")"

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

exec python3 agent.py