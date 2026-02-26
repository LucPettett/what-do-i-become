#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRAMEWORK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$FRAMEWORK_DIR/.." && pwd)"
DEVICES_DIR="$PROJECT_ROOT/devices"
BACKUP_ROOT="$DEVICES_DIR/_resets"
ENV_FILE="$FRAMEWORK_DIR/.env"
DEVICE_ID_FILE="$FRAMEWORK_DIR/.device_id"

MODE="soft"
TARGET_DEVICE_ID=""
ASSUME_YES=0
MAKE_BACKUP=1
DRY_RUN=0

usage() {
  cat <<USAGE
Usage:
  ./src/device/reset_device_memory.sh [options]

Options:
  --soft                 Wipe device memory, keep current device UUID (default)
  --hard                 Wipe device memory and rotate device UUID on next setup
  --device-id <uuid>     Target a specific device UUID (default: current UUID)
  --no-backup            Skip creating a rollback backup under devices/_resets/
  --dry-run              Print planned actions only
  --yes                  Do not prompt for confirmation
  -h, --help             Show this help

Examples:
  ./src/device/reset_device_memory.sh --soft --yes
  ./src/device/reset_device_memory.sh --hard --yes
  ./src/device/reset_device_memory.sh --device-id <uuid> --soft --yes
USAGE
}

read_env_value() {
  local key="$1"
  local file="$2"
  awk -F= -v target="$key" '$1==target {print substr($0, index($0,$2)); exit}' "$file" 2>/dev/null \
    | sed 's/^[[:space:]]*//; s/[[:space:]]*$//'
}

set_env_value() {
  local key="$1"
  local value="$2"
  local file="$3"
  local tmp
  tmp="$(mktemp)"

  if [ ! -f "$file" ]; then
    printf '%s=%s\n' "$key" "$value" > "$file"
    return 0
  fi

  awk -F= -v k="$key" -v v="$value" '
    BEGIN { done=0 }
    $1==k { print k "=" v; done=1; next }
    { print }
    END { if (!done) print k "=" v }
  ' "$file" > "$tmp"

  mv "$tmp" "$file"
}

is_uuid() {
  local raw="$1"
  [[ "$raw" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]
}

resolve_device_id() {
  local candidate=""

  if [ -n "$TARGET_DEVICE_ID" ]; then
    candidate="$TARGET_DEVICE_ID"
  elif [ -f "$DEVICE_ID_FILE" ]; then
    candidate="$(tr -d '[:space:]' < "$DEVICE_ID_FILE")"
  elif [ -f "$ENV_FILE" ]; then
    candidate="$(read_env_value WDIB_DEVICE_ID "$ENV_FILE" || true)"
  fi

  printf '%s' "$candidate"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --soft)
      MODE="soft"
      shift
      ;;
    --hard)
      MODE="hard"
      shift
      ;;
    --device-id)
      TARGET_DEVICE_ID="${2:-}"
      shift 2
      ;;
    --no-backup)
      MAKE_BACKUP=0
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --yes)
      ASSUME_YES=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

DEVICE_ID="$(resolve_device_id)"
if ! is_uuid "$DEVICE_ID"; then
  echo "Could not resolve a valid device UUID. Use --device-id <uuid>." >&2
  exit 1
fi

DEVICE_DIR="$DEVICES_DIR/$DEVICE_ID"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/${TIMESTAMP}_${DEVICE_ID}"

if [ "$MODE" != "soft" ] && [ "$MODE" != "hard" ]; then
  echo "Invalid mode: $MODE" >&2
  exit 2
fi

if [ "$DRY_RUN" -eq 1 ]; then
  ASSUME_YES=1
fi

echo "[INFO] Target device UUID: $DEVICE_ID"
echo "[INFO] Mode: $MODE"
echo "[INFO] Device directory: $DEVICE_DIR"
if [ "$MAKE_BACKUP" -eq 1 ]; then
  echo "[INFO] Backup directory: $BACKUP_DIR"
fi

if [ "$ASSUME_YES" -ne 1 ]; then
  echo ""
  echo "This will remove runtime memory/state for the target device."
  if [ "$MODE" = "hard" ]; then
    echo "Hard mode will also clear src/.device_id and WDIB_DEVICE_ID in src/.env."
  fi
  printf "Continue? [y/N]: "
  read -r answer
  case "${answer:-}" in
    y|Y|yes|YES)
      ;;
    *)
      echo "Aborted."
      exit 0
      ;;
  esac
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "[DRY-RUN] Would reset device memory now."
  echo "[DRY-RUN] Next commands after reset: ./src/setup.sh && ./src/run.sh"
  exit 0
fi

mkdir -p "$DEVICES_DIR"

if [ "$MAKE_BACKUP" -eq 1 ] && [ -d "$DEVICE_DIR" ]; then
  mkdir -p "$BACKUP_DIR"
  cp -a "$DEVICE_DIR" "$BACKUP_DIR/"
  {
    echo "created_at=$(date -Is)"
    echo "mode=$MODE"
    echo "device_id=$DEVICE_ID"
    echo "source_device_dir=$DEVICE_DIR"
  } > "$BACKUP_DIR/reset.meta"
  echo "[OK] Backup created: $BACKUP_DIR"
fi

if [ -d "$DEVICE_DIR" ]; then
  rm -rf "$DEVICE_DIR"
  echo "[OK] Removed device memory: $DEVICE_DIR"
else
  echo "[INFO] Device directory not found, nothing to delete"
fi

if [ "$MODE" = "hard" ]; then
  rm -f "$DEVICE_ID_FILE"
  if [ -f "$ENV_FILE" ]; then
    set_env_value WDIB_DEVICE_ID "" "$ENV_FILE"
  fi
  echo "[OK] Cleared local device identity; next setup will generate a new UUID"
fi

echo ""
echo "Reset complete."
echo "Next steps:"
echo "  1) ./src/setup.sh"
echo "  2) ./src/run.sh"

if [ "$MAKE_BACKUP" -eq 1 ]; then
  echo ""
  echo "Rollback from backup (if needed):"
  echo "  cp -a \"$BACKUP_DIR/$DEVICE_ID\" \"$DEVICES_DIR/$DEVICE_ID\""
  if [ "$MODE" = "hard" ]; then
    echo "  printf '%s\n' \"$DEVICE_ID\" > \"$DEVICE_ID_FILE\""
    echo "  # Optional: set WDIB_DEVICE_ID in src/.env back to $DEVICE_ID"
  fi
fi
