#!/usr/bin/env bash
# First-time setup for what-do-i-become.
# Run once on a fresh host machine: chmod +x src/setup.sh && ./src/setup.sh

set -euo pipefail

FRAMEWORK_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$FRAMEWORK_DIR/.." && pwd)"
ENV_FILE="$FRAMEWORK_DIR/.env"
DEVICE_ID_FILE="$FRAMEWORK_DIR/.device_id"

cd "$PROJECT_ROOT"

echo "=========================================================="
echo "  what-do-i-become - First-Time Setup"
echo "=========================================================="

echo ""
echo "-> Installing system packages (best effort)..."
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3 python3-pip git i2c-tools
elif command -v brew >/dev/null 2>&1; then
  brew install python git >/dev/null 2>&1 || true
  echo "  (brew detected; installed python/git if needed)"
else
  echo "  (no supported package manager detected; skipping system package install)"
fi

echo ""
echo "-> Installing Python packages..."
if command -v python3 >/dev/null 2>&1; then
  python3 -m pip install --break-system-packages openai pyyaml 2>/dev/null \
    || python3 -m pip install openai pyyaml
else
  echo "  python3 is required but was not found in PATH"
  exit 1
fi

echo ""
echo "-> Enabling I2C and camera interfaces..."
if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_i2c 0 2>/dev/null || echo "  (I2C skipped/already enabled)"
  sudo raspi-config nonint do_camera 0 2>/dev/null || echo "  (camera skipped/already enabled)"
else
  echo "  (raspi-config not found; skipping Pi-specific interface setup)"
fi

mkdir -p "$PROJECT_ROOT/devices"

if [ ! -f "$ENV_FILE" ]; then
  cp "$FRAMEWORK_DIR/.env.example" "$ENV_FILE"
  echo "-> Created src/.env from template"
else
  echo "-> src/.env already exists"
fi

read_env_value() {
  local key="$1"
  local file="$2"
  awk -F= -v target="$key" '$1==target {print substr($0, index($0,$2)); exit}' "$file" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//'
}

set_env_value() {
  local key="$1"
  local value="$2"
  local file="$3"
  if grep -q "^${key}=" "$file"; then
    if sed --version >/dev/null 2>&1; then
      sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
      sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
    fi
  else
    printf "\n%s=%s\n" "$key" "$value" >> "$file"
  fi
}

is_true() {
  local raw="${1:-}"
  local normalized
  normalized="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  case "$normalized" in
    1|true|yes|on)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

validate_uuid() {
  local candidate="$1"
  python3 - "$candidate" <<'PY'
import sys
import uuid
try:
    print(uuid.UUID(sys.argv[1]))
except Exception:
    raise SystemExit(1)
PY
}

DEVICE_ID=""
if [ -f "$DEVICE_ID_FILE" ]; then
  DEVICE_ID="$(tr -d '[:space:]' < "$DEVICE_ID_FILE")"
fi

if [ -z "$DEVICE_ID" ] && [ -f "$ENV_FILE" ]; then
  DEVICE_ID="$(read_env_value WDIB_DEVICE_ID "$ENV_FILE" || true)"
fi

if [ -n "$DEVICE_ID" ]; then
  if ! DEVICE_ID="$(validate_uuid "$DEVICE_ID")"; then
    echo "  Existing WDIB_DEVICE_ID is invalid. Generating a new UUID."
    DEVICE_ID=""
  fi
fi

if [ -z "$DEVICE_ID" ]; then
  DEVICE_ID="$(python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"
fi

echo "$DEVICE_ID" > "$DEVICE_ID_FILE"
set_env_value WDIB_DEVICE_ID "$DEVICE_ID" "$ENV_FILE"

GIT_REMOTE="$(read_env_value WDIB_GIT_REMOTE "$ENV_FILE" || true)"
GIT_BRANCH="$(read_env_value WDIB_GIT_BRANCH "$ENV_FILE" || true)"
GIT_AUTO_PUSH="$(read_env_value WDIB_GIT_AUTO_PUSH "$ENV_FILE" || true)"
GIT_USER_NAME="$(read_env_value WDIB_GIT_USER_NAME "$ENV_FILE" || true)"
GIT_USER_EMAIL="$(read_env_value WDIB_GIT_USER_EMAIL "$ENV_FILE" || true)"
GIT_REMOTE_URL="$(read_env_value WDIB_GIT_REMOTE_URL "$ENV_FILE" || true)"

if [ -z "$GIT_REMOTE" ]; then
  GIT_REMOTE="origin"
fi
if [ -z "$GIT_AUTO_PUSH" ]; then
  GIT_AUTO_PUSH="true"
fi

export PROJECT_ROOT
export WDIB_DEVICE_ID="$DEVICE_ID"

python3 - <<'PY'
import os
import platform
import subprocess
from datetime import date
from pathlib import Path

import yaml


def detect_board():
    model = Path('/proc/device-tree/model')
    if model.exists():
        try:
            return model.read_bytes().replace(b'\x00', b'').decode('utf-8', errors='ignore').strip()
        except OSError:
            pass

    if platform.system() == 'Darwin':
        try:
            board = subprocess.check_output(['sysctl', '-n', 'hw.model'], text=True).strip()
            if board:
                return board
        except Exception:
            pass

    return platform.node() or platform.machine() or 'unknown'


def detect_ram():
    try:
        page_size = os.sysconf('SC_PAGE_SIZE')
        phys_pages = os.sysconf('SC_PHYS_PAGES')
        gib = (page_size * phys_pages) / float(1024 ** 3)
        return f"{gib:.1f} GB"
    except (ValueError, OSError, AttributeError):
        return 'unknown'


def detect_os():
    os_release = Path('/etc/os-release')
    if os_release.exists():
        for line in os_release.read_text(encoding='utf-8').splitlines():
            if line.startswith('PRETTY_NAME='):
                return line.split('=', 1)[1].strip().strip('"')
    return f"{platform.system()} {platform.release()}".strip()


project_root = Path(os.environ['PROJECT_ROOT'])
device_id = os.environ['WDIB_DEVICE_ID']
device_dir = project_root / 'devices' / device_id
sessions_dir = device_dir / 'sessions'
device_yaml = device_dir / 'device.yaml'
notes_file = device_dir / 'notes.md'

device_dir.mkdir(parents=True, exist_ok=True)
sessions_dir.mkdir(parents=True, exist_ok=True)

if not notes_file.exists():
    notes_file.write_text('', encoding='utf-8')

if not device_yaml.exists():
    payload = {
        'id': device_id,
        'awoke': date.today().isoformat(),
        'day': 0,
        'last_session': None,
        'hardware': {
            'board': detect_board(),
            'ram': detect_ram(),
            'os': detect_os(),
            'arch': platform.machine() or 'unknown',
        },
        'becoming': '',
        'status': 'FIRST_RUN',
        'parts': [],
        'part_requested': None,
        'last_summary': '',
    }
    device_yaml.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=120),
        encoding='utf-8',
    )
PY

chmod +x "$FRAMEWORK_DIR/run.sh" "$FRAMEWORK_DIR/setup.sh"

echo ""
echo "-> Setting up daily cron job (9:00 AM)..."
CRON_CMD="0 9 * * * cd ${FRAMEWORK_DIR} && ./run.sh >> ${PROJECT_ROOT}/cron.log 2>&1"
if command -v crontab >/dev/null 2>&1; then
  ( crontab -l 2>/dev/null | grep -v "what-do-i-become\|src/run\.sh\|${FRAMEWORK_DIR}" ; echo "$CRON_CMD" ) | crontab -
  echo "  Installed: $CRON_CMD"
else
  echo "  (crontab not found; skipping scheduler setup)"
fi

echo ""
echo "-> Preparing first commit for this device..."
if [ ! -d .git ]; then
  git init
fi

if [ -n "$GIT_USER_NAME" ]; then
  git config user.name "$GIT_USER_NAME"
fi
if [ -n "$GIT_USER_EMAIL" ]; then
  git config user.email "$GIT_USER_EMAIL"
fi

if [ -n "$GIT_REMOTE_URL" ]; then
  if git remote get-url "$GIT_REMOTE" >/dev/null 2>&1; then
    CURRENT_REMOTE_URL="$(git remote get-url "$GIT_REMOTE" 2>/dev/null || true)"
    if [ "$CURRENT_REMOTE_URL" != "$GIT_REMOTE_URL" ]; then
      git remote set-url "$GIT_REMOTE" "$GIT_REMOTE_URL"
      echo "  Updated git remote '$GIT_REMOTE' from WDIB_GIT_REMOTE_URL"
    fi
  else
    git remote add "$GIT_REMOTE" "$GIT_REMOTE_URL"
    echo "  Added git remote '$GIT_REMOTE' from WDIB_GIT_REMOTE_URL"
  fi
fi

SHORT_ID="${DEVICE_ID:0:8}"
TODAY="$(date +%F)"

git add "devices/${DEVICE_ID}"
if ! git diff --cached --quiet -- "devices/${DEVICE_ID}"; then
  git commit -m "${SHORT_ID} awoke (${TODAY})" -- "devices/${DEVICE_ID}" || true
else
  echo "  No new device files to commit"
fi

if is_true "$GIT_AUTO_PUSH"; then
  if git remote get-url "$GIT_REMOTE" >/dev/null 2>&1; then
    PUSH_ARGS=("$GIT_REMOTE")
    if [ -n "$GIT_BRANCH" ]; then
      PUSH_ARGS+=("HEAD:${GIT_BRANCH}")
    fi
    if git push "${PUSH_ARGS[@]}"; then
      echo "  Pushed initial device commit"
    else
      echo "  Push failed; you can push manually later"
    fi
  else
    echo "  No git remote configured for '$GIT_REMOTE' (skipping push)"
  fi
else
  echo "  WDIB_GIT_AUTO_PUSH=false (skipping push)"
fi

echo ""
echo "=========================================================="
echo "  Setup complete"
echo ""
echo "  Device ID: ${DEVICE_ID}"
echo "  Short ID:  ${SHORT_ID}"
echo ""
echo "  Next steps:"
echo "    1. Edit src/.env (provider/model/API key, optional WDIB_GIT_REMOTE_URL)"
echo "    2. Ensure git auth works (SSH key, PAT, or credential helper)"
echo "    3. Optional: cp src/SPIRIT.md.example src/SPIRIT.md"
echo "    4. Run manually: ./src/run.sh"
echo "    5. Device files now live in: devices/${DEVICE_ID}/"
echo "=========================================================="
