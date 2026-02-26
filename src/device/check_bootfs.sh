#!/usr/bin/env bash
set -euo pipefail

BOOTFS="${1:-/Volumes/bootfs}"
EXIT_CODE=0

fail() {
  echo "[FAIL] $1"
  EXIT_CODE=1
}

ok() {
  echo "[OK]   $1"
}

info() {
  echo "[INFO] $1"
}

if [ ! -d "$BOOTFS" ]; then
  fail "Boot partition not found at $BOOTFS"
  echo "Usage: ./src/device/check_bootfs.sh /path/to/bootfs"
  exit "$EXIT_CODE"
fi

info "Checking Raspberry Pi boot partition: $BOOTFS"

if [ -f "$BOOTFS/config.txt" ]; then
  ok "config.txt present"
else
  fail "config.txt missing"
fi

if [ -f "$BOOTFS/cmdline.txt" ]; then
  ok "cmdline.txt present"
else
  fail "cmdline.txt missing"
fi

if [ -f "$BOOTFS/ssh" ]; then
  ok "SSH enable marker present (ssh)"
else
  info "SSH enable marker missing (create '$BOOTFS/ssh' to enable SSH on first boot)"
fi

if [ -f "$BOOTFS/wpa_supplicant.conf" ]; then
  SSID_LINE="$(grep -E '^[[:space:]]*ssid=' "$BOOTFS/wpa_supplicant.conf" | head -n 1 || true)"
  PSK_LINE="$(grep -E '^[[:space:]]*psk=' "$BOOTFS/wpa_supplicant.conf" | head -n 1 || true)"
  if [ -n "$SSID_LINE" ] && [ -n "$PSK_LINE" ]; then
    ok "wpa_supplicant.conf has SSID and PSK"
  else
    info "wpa_supplicant.conf exists but is missing SSID/PSK"
  fi
else
  info "wpa_supplicant.conf not found"
fi

if [ -f "$BOOTFS/network-config" ]; then
  ok "network-config present (cloud-init network path available)"
else
  info "network-config missing"
fi

if [ -f "$BOOTFS/userconf.txt" ]; then
  ok "userconf.txt present (first-boot user credential seed)"
else
  info "userconf.txt missing"
fi

if [ -f "$BOOTFS/wdib-secrets.env" ]; then
  ok "wdib-secrets.env present"
  for key in OPENAI_API_KEY WDIB_GIT_REMOTE_URL WDIB_LLM_PROVIDER WDIB_LLM_MODEL; do
    value="$(sed -n "s/^${key}=//p" "$BOOTFS/wdib-secrets.env" | head -n 1 || true)"
    if [ -z "$value" ]; then
      info "$key is missing"
    else
      case "$value" in
        sk-your-key-here|your-anthropic-key-here|your-xai-key-here|your-google-ai-key-here)
          info "$key is placeholder"
          ;;
        *)
          ok "$key is set"
          ;;
      esac
    fi
  done
else
  info "wdib-secrets.env not found"
fi

if [ -f "$BOOTFS/wdib-status.txt" ]; then
  RESULT="$(sed -n 's/^result=//p' "$BOOTFS/wdib-status.txt" | head -n 1 || true)"
  DETAIL="$(sed -n 's/^detail=//p' "$BOOTFS/wdib-status.txt" | head -n 1 || true)"
  if [ -n "$RESULT" ]; then
    info "Last bootstrap result: $RESULT${DETAIL:+ ($DETAIL)}"
  else
    info "wdib-status.txt present but no result field found"
  fi
fi

if [ "$EXIT_CODE" -eq 0 ]; then
  info "SD card preflight complete"
fi

exit "$EXIT_CODE"
