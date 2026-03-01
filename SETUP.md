# Setup Guide

WDIB setup is intentionally split into two steps:

1. **Prepare your device**
2. **Setup WDIB on your device**

This keeps first boot reliable and moves mutable setup to SSH where iteration is faster.

You will need:

- Your fork URL (for example `https://github.com/<you>/what-do-i-become.git`).
- Wi-Fi SSID/password for the device
- `OPENAI_API_KEY` (or your chosen provider key)
- Optional: a local spirit file (for example `src/SPIRIT.beach-cleanup.example.md` or `src/SPIRIT.daily-dashboard.example.md`)
- Optional: Slack Incoming Webhook URL (for daily sanitized updates)

## Prepare Your Device

Your device can be prepared by you, or by Codex.

### Codex-Assisted

```bash
codex exec --yolo "prepare my Raspberry Pi SD card for what-do-i-become using /Volumes/bootfs. Ensure SSH is enabled, Wi-Fi is configured, and print a readiness checklist only."
```

### Manual

```bash
./src/device/check_bootfs.sh /Volumes/bootfs
```

This validates the boot partition and shows whether SSH/network/bootstrap files are present.

Minimum expected outcome before ejecting card:

- `/Volumes/bootfs/ssh` exists
- network config is present (`wpa_supplicant.conf` and/or `network-config`)
- no blocking filesystem errors from `check_bootfs.sh`

## Setup WDIB On Your Device

After the Pi boots and has an IP address, setup can be done by you or by Codex.

### Codex-Assisted

```bash
codex exec --yolo "SSH into <device_ip> and bootstrap what-do-i-become from https://github.com/<you>/what-do-i-become.git. Configure src/.env with my API key, run setup, run once, and report exactly what is still blocking."
```

### Codex-Assisted (With Spirit)

```bash
codex exec --yolo "SSH into <device_ip> and run ./src/device/bootstrap_over_ssh.sh --host <device_ip> --user pi --repo https://github.com/<you>/what-do-i-become.git --openai-api-key '$OPENAI_API_KEY' --spirit-file ./src/SPIRIT.beach-cleanup.example.md, then report exactly what is still blocking."
```

### Manual

```bash
./src/device/bootstrap_over_ssh.sh \
  --host <device_ip> \
  --user pi \
  --repo https://github.com/<you>/what-do-i-become.git \
  --openai-api-key "$OPENAI_API_KEY" \
  --spirit-file ./src/SPIRIT.beach-cleanup.example.md
```

Use `./src/SPIRIT.daily-dashboard.example.md` instead when the mission is a daily local/global dashboard briefing.

This script:

- installs required packages
- clones/pulls the repo on device
- creates `~/.ssh/wdib_repo` deploy key (if missing)
- sets `origin` to `git@github-wdib:<you>/what-do-i-become.git` for GitHub repos
- writes `src/.env` values (`WDIB_LLM_PROVIDER`, `WDIB_LLM_MODEL`, optional `OPENAI_API_KEY`, `WDIB_GIT_REMOTE_URL`)
- uploads `src/SPIRIT.md` before first setup/run when `--spirit-file` is provided
- runs `./src/setup.sh` and one `./src/run.sh`

### Optional: Enable Slack notifications

On the device (`src/.env`):

```bash
WDIB_NOTIFICATION_CHANNELS=slack
WDIB_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
WDIB_SLACK_USERNAME=wdib
WDIB_SLACK_AWAKENING_EMOJI=:sunrise:
WDIB_SLACK_UPDATE_EMOJI=☕️
```

Notifications are routed through a modular channel router (`src/wdib/notifications/`), so more channels can be added later without changing the core tick flow.

### Important Deploy-Key Step

`bootstrap_over_ssh.sh` prints the device public key between:

- `=== WDIB_DEPLOY_KEY_PUBLIC ===`
- `=== WDIB_DEPLOY_KEY_PUBLIC_END ===`

Add that key in GitHub:

1. `Settings` -> `Deploy keys` -> `Add deploy key`
2. paste the printed key
3. enable **Allow write access**

Then rerun setup once to confirm push auth.

## Quick Verification

On the device (or via SSH):

```bash
cd ~/development/what-do-i-become
git remote -v
./src/run.sh
```

In GitHub, confirm new commits under `devices/<uuid>/public/`.

## Reset and Rollback

When you need to wipe a device's memory/state and start fresh, run:

```bash
./src/device/reset_device_memory.sh --soft --yes
```

Modes:

- `--soft`: clears `devices/<uuid>/` memory, keeps same device UUID.
- `--hard`: clears memory and rotates UUID on next `./src/setup.sh`.

Examples:

```bash
# Keep same UUID
./src/device/reset_device_memory.sh --soft --yes

# New UUID on next setup
./src/device/reset_device_memory.sh --hard --yes
```

By default, reset creates a rollback backup at `devices/_resets/<timestamp>_<uuid>/`.

Then reinitialize:

```bash
./src/setup.sh
./src/run.sh
```

## Skills

Bundled skills live in `src/skills/`.

Add your own skills in `skills/<name>/SKILL.md`. User skills are loaded with higher precedence than bundled skills, so matching names override bundled behavior.

## Safety and termination

All safety policy and termination procedures are documented in [`SAFETY.md`](./SAFETY.md).
