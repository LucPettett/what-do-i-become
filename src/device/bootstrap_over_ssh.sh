#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage:
  ./src/device/bootstrap_over_ssh.sh --host <device_ip_or_host> --repo <git_url> [options]

Required:
  --host <host>              Device host/IP reachable over SSH
  --repo <git_url>           Fork URL (https or ssh)

Optional:
  --user <name>              SSH user (default: pi)
  --port <port>              SSH port (default: 22)
  --openai-api-key <key>     OPENAI_API_KEY to write into src/.env
  --spirit-file <path>       Local SPIRIT.md file to upload before first run
  --skip-run                 Skip initial ./src/run.sh

Example:
  ./src/device/bootstrap_over_ssh.sh \\
    --host 192.168.4.173 \\
    --repo https://github.com/<you>/what-do-i-become.git \\
    --openai-api-key "\$OPENAI_API_KEY" \\
    --spirit-file ./src/SPIRIT.security-monitoring.example.md
USAGE
}

github_slug_from_url() {
  local url="$1"
  local slug=""

  case "$url" in
    https://github.com/*)
      slug="${url#https://github.com/}"
      ;;
    http://github.com/*)
      slug="${url#http://github.com/}"
      ;;
    git@github.com:*)
      slug="${url#git@github.com:}"
      ;;
    ssh://git@github.com/*)
      slug="${url#ssh://git@github.com/}"
      ;;
    *)
      return 1
      ;;
  esac

  slug="${slug%.git}"
  if [[ "$slug" == */* ]]; then
    printf '%s\n' "$slug"
    return 0
  fi
  return 1
}

HOST=""
USER="pi"
PORT="22"
REPO_URL=""
OPENAI_API_KEY=""
SPIRIT_FILE_PATH=""
SPIRIT_B64=""
RUN_ONCE="1"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --user)
      USER="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    --repo)
      REPO_URL="${2:-}"
      shift 2
      ;;
    --openai-api-key)
      OPENAI_API_KEY="${2:-}"
      shift 2
      ;;
    --spirit-file)
      SPIRIT_FILE_PATH="${2:-}"
      shift 2
      ;;
    --skip-run)
      RUN_ONCE="0"
      shift 1
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

if [ -z "$HOST" ] || [ -z "$REPO_URL" ]; then
  usage
  exit 2
fi

if [ -n "$SPIRIT_FILE_PATH" ]; then
  if [ ! -f "$SPIRIT_FILE_PATH" ]; then
    echo "[ERR] --spirit-file not found: $SPIRIT_FILE_PATH" >&2
    exit 2
  fi
  if command -v base64 >/dev/null 2>&1; then
    SPIRIT_B64="$(base64 < "$SPIRIT_FILE_PATH" | tr -d '\n')"
  else
    SPIRIT_B64="$(python3 - "$SPIRIT_FILE_PATH" <<'PY'
import base64
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
print(base64.b64encode(path.read_bytes()).decode("ascii"), end="")
PY
)"
  fi
fi

CLONE_URL="$REPO_URL"
REMOTE_URL=""
if SLUG="$(github_slug_from_url "$REPO_URL" 2>/dev/null)"; then
  CLONE_URL="https://github.com/${SLUG}.git"
  REMOTE_URL="git@github-wdib:${SLUG}.git"
fi

SSH_TARGET="${USER}@${HOST}"
SSH_OPTS=(
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=10
  -p "$PORT"
)

echo "[INFO] SSH target: $SSH_TARGET"
echo "[INFO] Clone URL: $CLONE_URL"
if [ -n "$REMOTE_URL" ]; then
  echo "[INFO] Push URL:  $REMOTE_URL"
fi

ssh "${SSH_OPTS[@]}" "$SSH_TARGET" bash -s -- "$CLONE_URL" "$REMOTE_URL" "$OPENAI_API_KEY" "$RUN_ONCE" "$SPIRIT_B64" <<'REMOTE'
set -euo pipefail

CLONE_URL="$1"
REMOTE_URL="$2"
OPENAI_API_KEY="$3"
RUN_ONCE="$4"
SPIRIT_B64="$5"

REPO_DIR="$HOME/development/what-do-i-become"
SSH_DIR="$HOME/.ssh"

set_env_value() {
  local key="$1"
  local value="$2"
  local file="$3"
  local tmp_file
  tmp_file="$(mktemp)"

  awk -v k="$key" -v v="$value" '
    BEGIN { done=0 }
    $0 ~ "^" k "=" { print k "=" v; done=1; next }
    { print }
    END { if (!done) print k "=" v }
  ' "$file" > "$tmp_file"

  mv "$tmp_file" "$file"
}

if command -v apt-get >/dev/null 2>&1; then
  if sudo -n true >/dev/null 2>&1; then
    sudo apt-get update -qq || true
    sudo apt-get install -y -qq python3 python3-pip git i2c-tools || true
  else
    echo "[WARN] Skipping apt install (sudo requires interactive password)"
  fi
fi

mkdir -p "$HOME/development"
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "$CLONE_URL" "$REPO_DIR"
fi

cd "$REPO_DIR"
git pull --ff-only || true

mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
if [ ! -f "$SSH_DIR/wdib_repo" ]; then
  ssh-keygen -t ed25519 -f "$SSH_DIR/wdib_repo" -C "wdib-$(hostname)-$(date +%F)" -N "" >/dev/null
  echo "[INFO] Created deploy key: $SSH_DIR/wdib_repo"
fi

if ! grep -q '^Host github-wdib$' "$SSH_DIR/config" 2>/dev/null; then
  cat >> "$SSH_DIR/config" <<'CONF'
Host github-wdib
  HostName github.com
  User git
  IdentityFile ~/.ssh/wdib_repo
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
CONF
fi
chmod 600 "$SSH_DIR/config"

echo ""
echo "=== WDIB_DEPLOY_KEY_PUBLIC ==="
cat "$SSH_DIR/wdib_repo.pub"
echo "=== WDIB_DEPLOY_KEY_PUBLIC_END ==="
echo ""

if [ -n "$REMOTE_URL" ]; then
  git remote set-url origin "$REMOTE_URL"
fi

if [ ! -f src/.env ]; then
  cp src/.env.example src/.env
fi

set_env_value WDIB_LLM_PROVIDER openai src/.env
set_env_value WDIB_LLM_MODEL gpt-5.2 src/.env
if [ -n "$OPENAI_API_KEY" ]; then
  set_env_value OPENAI_API_KEY "$OPENAI_API_KEY" src/.env
fi
if [ -n "$REMOTE_URL" ]; then
  set_env_value WDIB_GIT_REMOTE_URL "$REMOTE_URL" src/.env
fi
if [ -n "$SPIRIT_B64" ]; then
  if command -v base64 >/dev/null 2>&1; then
    printf '%s' "$SPIRIT_B64" | base64 -d > src/SPIRIT.md \
      || printf '%s' "$SPIRIT_B64" | base64 --decode > src/SPIRIT.md
  else
    python3 - "$SPIRIT_B64" <<'PY'
import base64
import pathlib
import sys

payload = sys.argv[1].encode("ascii")
pathlib.Path("src/SPIRIT.md").write_bytes(base64.b64decode(payload))
PY
  fi
  echo "[INFO] Uploaded SPIRIT.md from --spirit-file"
fi
chmod 600 src/.env || true

chmod +x src/setup.sh src/run.sh
./src/setup.sh

if [ "$RUN_ONCE" = "1" ]; then
  ./src/run.sh || true
fi

if [ -n "$REMOTE_URL" ]; then
  AUTH_OUT="$(ssh -T -o BatchMode=yes -o ConnectTimeout=10 git@github-wdib 2>&1 || true)"
  if echo "$AUTH_OUT" | grep -qi "successfully authenticated"; then
    echo "[OK] github-wdib auth works"
  else
    echo "[WARN] github-wdib auth is not ready yet"
    echo "[WARN] Add the deploy key above in GitHub: Settings -> Deploy keys -> Allow write access"
  fi
fi

echo "[INFO] Bootstrap over SSH complete"
REMOTE
