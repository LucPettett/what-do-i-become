#!/usr/bin/env bash
# Wrapper script: load src/.env then run WDIB control-plane tick.

set -euo pipefail

FRAMEWORK_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$FRAMEWORK_DIR"

# Cron may run with a minimal PATH that omits /usr/local/bin where codex is installed.
PATH="${PATH:-/usr/bin:/bin}"
case ":$PATH:" in
  *:/usr/local/bin:*) ;;
  *) PATH="/usr/local/bin:$PATH" ;;
esac
export PATH

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

exec python3 -m wdib.cli tick --pretty
