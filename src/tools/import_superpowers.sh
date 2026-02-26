#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_ROOT="$PROJECT_ROOT/src/skills"

UPSTREAM_REPO="https://github.com/obra/superpowers.git"
UPSTREAM_REF=""
SOURCE_PATH=""
MODE="core"
DRY_RUN=0

CORE_SKILLS=(
  "systematic-debugging"
  "test-driven-development"
  "verification-before-completion"
)

usage() {
  cat <<USAGE
Usage:
  ./src/tools/import_superpowers.sh [options]

Options:
  --core                  Import curated core skills (default)
  --all                   Import all upstream skills except using-superpowers
  --source <path>         Use an existing local checkout instead of cloning
  --ref <git-ref>         Upstream ref when cloning (branch/tag/commit)
  --dry-run               Show actions without copying files
  -h, --help              Show this help

Examples:
  ./src/tools/import_superpowers.sh --core
  ./src/tools/import_superpowers.sh --all --ref main
  ./src/tools/import_superpowers.sh --source /tmp/superpowers --core
USAGE
}

log() {
  echo "[INFO] $1"
}

warn() {
  echo "[WARN] $1"
}

now_iso() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --core)
      MODE="core"
      shift
      ;;
    --all)
      MODE="all"
      shift
      ;;
    --source)
      SOURCE_PATH="${2:-}"
      shift 2
      ;;
    --ref)
      UPSTREAM_REF="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
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

if [ ! -d "$TARGET_ROOT" ]; then
  echo "Target skills directory not found: $TARGET_ROOT" >&2
  exit 1
fi

CLEANUP_PATH=""
if [ -n "$SOURCE_PATH" ]; then
  if [ ! -d "$SOURCE_PATH/.git" ] && [ ! -d "$SOURCE_PATH/skills" ]; then
    echo "Invalid source path: $SOURCE_PATH" >&2
    exit 1
  fi
  SOURCE_DIR="$SOURCE_PATH"
else
  SOURCE_DIR="$(mktemp -d /tmp/wdib-superpowers.XXXXXX)"
  CLEANUP_PATH="$SOURCE_DIR"
  log "Cloning $UPSTREAM_REPO"
  git clone --depth 1 "$UPSTREAM_REPO" "$SOURCE_DIR" >/dev/null
  if [ -n "$UPSTREAM_REF" ]; then
    git -C "$SOURCE_DIR" fetch --depth 1 origin "$UPSTREAM_REF" >/dev/null
    git -C "$SOURCE_DIR" checkout "$UPSTREAM_REF" >/dev/null
  fi
fi

if [ ! -d "$SOURCE_DIR/skills" ]; then
  echo "No skills directory found in source: $SOURCE_DIR" >&2
  if [ -n "$CLEANUP_PATH" ]; then
    rm -rf "$CLEANUP_PATH"
  fi
  exit 1
fi

if [ "$MODE" = "core" ]; then
  SKILLS=("${CORE_SKILLS[@]}")
else
  SKILLS=()
  while IFS= read -r skill; do
    SKILLS+=("$skill")
  done < <(find "$SOURCE_DIR/skills" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)
  FILTERED=()
  for skill in "${SKILLS[@]}"; do
    if [ "$skill" = "using-superpowers" ]; then
      continue
    fi
    FILTERED+=("$skill")
  done
  SKILLS=("${FILTERED[@]}")
fi

if [ "${#SKILLS[@]}" -eq 0 ]; then
  echo "No skills selected for import" >&2
  if [ -n "$CLEANUP_PATH" ]; then
    rm -rf "$CLEANUP_PATH"
  fi
  exit 1
fi

for skill in "${SKILLS[@]}"; do
  if [ ! -f "$SOURCE_DIR/skills/$skill/SKILL.md" ]; then
    echo "Selected skill missing SKILL.md: $skill" >&2
    if [ -n "$CLEANUP_PATH" ]; then
      rm -rf "$CLEANUP_PATH"
    fi
    exit 1
  fi
done

if [ "$DRY_RUN" -eq 1 ]; then
  log "Dry run mode"
fi

for skill in "${SKILLS[@]}"; do
  src="$SOURCE_DIR/skills/$skill"
  dst="$TARGET_ROOT/$skill"
  log "Importing $skill -> $dst"
  if [ "$DRY_RUN" -eq 0 ]; then
    rm -rf "$dst"
    mkdir -p "$dst"
    cp -a "$src/." "$dst/"
  fi
done

if [ "$DRY_RUN" -eq 0 ]; then
  commit="unknown"
  if git -C "$SOURCE_DIR" rev-parse --short HEAD >/dev/null 2>&1; then
    commit="$(git -C "$SOURCE_DIR" rev-parse --short HEAD)"
  fi

  manifest="$TARGET_ROOT/SUPERPOWERS_IMPORT.md"
  {
    echo "# Superpowers Import"
    echo ""
    echo "Imported from: $UPSTREAM_REPO"
    if [ -n "$UPSTREAM_REF" ]; then
      echo "Ref: $UPSTREAM_REF"
    fi
    echo "Commit: $commit"
    echo "Imported at: $(now_iso)"
    echo ""
    echo "Imported skills:"
    for skill in "${SKILLS[@]}"; do
      echo "- $skill"
    done
    echo ""
    echo "Notes:"
    echo "- Upstream license: MIT (obra/superpowers)"
    echo "- 'using-superpowers' is excluded by default to avoid overriding project-level behavior rules."
  } > "$manifest"
  log "Wrote manifest: $manifest"
fi

if [ -n "$CLEANUP_PATH" ]; then
  rm -rf "$CLEANUP_PATH"
fi

log "Done"
