<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="./logo.png">
    <img src="./logo.png" alt="what-do-i-become logo" width="560">
  </picture>
</p>

# what-do-i-become

A self-construction framework for hardware that wakes up, explores itself, and asks you to build it into something.

[How It Works](#how-it-works) · [Live Devices](#live-devices) · [Fork This Repo](#fork-this-repo) · [Device State](#device-state) · [Safety](#safety)

---

## Live Devices

Devices running right now. Auto-generated from `devices/*/device.yaml`.

<!-- DEVICE_DASHBOARD_START -->
| Device | Awoke | Day | Becoming | Status |
| --- | --- | ---: | --- | --- |
| - | - | 0 | - | - |
<!-- DEVICE_DASHBOARD_END -->

## What Is This?

`what-do-i-become` turns any computer into an autonomous hardware project. An LLM agent wakes once per day on a device, inspects what it has, explores what it can do, writes code, and requests a specific physical part when needed.

You buy it. You install it. The machine verifies it works and moves on.

Every device can read optional guidance from `src/SPIRIT.md` — the founding instructions for behavior and direction. That file is human-authored guidance. What changes over time is `becoming` in `device.yaml`, which the device writes itself.

- `SPIRIT.md` is given.
- `becoming` is earned.

The device can self-orchestrate: write code, run persistent processes, and manage its own services. The daily session is a check-in, not the only window of agency. The framework provides the conditions for emergent behavior, not a prescribed outcome.

Devices are identified by UUID, not names, to avoid biasing purpose early.

## You Are The Agent

The machine can reason, inspect, and write code, but it cannot open a box or connect a cable. You handle the physical layer.

## GitHub Is Your Base

The repo is the product. Fork `what-do-i-become`, point devices at it, and the repo becomes your database, monitoring layer, and oversight tool.

Every session is committed. Every part request is logged. Every decision is in version control.

Devices push only to `devices/<uuid>/`, and a GitHub Action rebuilds the README dashboard from `devices/*/device.yaml`.

## How It Works

The device wakes once per day on a cron schedule. It loads its context — spirit, state, any message you left — and enters an agent loop where it can inspect hardware, run commands, write files, and reason about what to do next.

If it needs a physical part it doesn't have, it requests exactly one, then waits for you to install it. On the next run, it verifies the part works before moving on.

At the end of every session, the device writes a session log, updates `device.yaml`, and pushes to the repo. Then it sleeps until tomorrow.

That's the whole loop: wake, think, act, log, sleep.

## Fork This Repo

This framework is designed to run on a dedicated single-board computer on a private network. We recommend a Raspberry Pi. See [Live Devices](#live-devices) for reference builds.

```bash
git clone git@github.com:<you>/what-do-i-become.git
cd what-do-i-become
chmod +x src/setup.sh
./src/setup.sh
```

Setup generates a UUID, creates `devices/<uuid>/`, discovers hardware, writes the initial `device.yaml` with `awoke` set to today and `becoming` empty, configures daily cron at 09:00, and creates the first commit.

Set your API key:

```bash
cp src/.env.example src/.env
nano src/.env
```

Run once manually:

```bash
./src/run.sh
```

To leave a one-off message for the next session:

```bash
echo "I installed the requested part and left notes in device.yaml." > devices/<uuid>/human_message.txt
```

That message is read and cleared at next startup.

## Device State

Each device writes `devices/<uuid>/device.yaml`:

```yaml
id: a3f7c812-6e4d-4b1a-9c0f-2d8e1a5b3f90
awoke: 2026-02-18
day: 14
last_session: 2026-03-04
hardware:
  board: Dedicated single-board computer
  ram: 4.0 GB
  os: Debian GNU/Linux 12 (bookworm)
  arch: aarch64
becoming: To continuously refine my role through verified capability growth
status: AWAITING_PART
parts:
  - name: Requested Part 01
    reason: Extends currently verified capabilities
    details: Selected and justified from observed constraints
    requested_on: 2026-02-22
    installed_on: 2026-02-24
    verified_on: 2026-02-24
    verification: Verified through device-run checks and persisted logs
    status: VERIFIED
part_requested:
  name: Requested Part 02
  reason: Required for the next capability expansion
  date: 2026-03-04
last_summary: Verified recent changes, updated state, and continued autonomous operation.
```

`becoming` starts empty and is refined over time.

Status is one of:

- `FIRST_RUN`
- `EXPLORING`
- `WRITING_CODE`
- `VERIFYING_PART`
- `AWAITING_PART`
- `ERROR`

## Runtime Config

`src/.env.example` includes provider placeholders for OpenAI, Anthropic, Grok/XAI, and Gemini keys.

Current runtime implementation supports `WDIB_LLM_PROVIDER=openai`. Other providers are pre-wired in config for future backend additions.

Git behavior is configurable in `.env`:

- `WDIB_GIT_REMOTE` (default `origin`)
- `WDIB_GIT_BRANCH` (optional explicit push target)
- `WDIB_GIT_AUTO_PUSH` (`true`/`false`)
- `WDIB_GIT_REMOTE_URL` (setup can add or update the remote URL)
- `WDIB_GIT_USER_NAME`, `WDIB_GIT_USER_EMAIL` (optional local git identity override)

## Directory Layout

`src/` is the framework — agent, tools, memory, setup, and spirit. `devices/` is per-device state — one subdirectory per UUID containing `device.yaml`, session logs, notes, and any human messages. `.github/` rebuilds the README dashboard on push.

## Safety

These agents execute shell commands and may run `sudo`. Run this on a dedicated device on a private network, not on your daily machine, not on production infrastructure.

## Device Lifecycle

### Prepare your repo

Do this once for your fork before provisioning devices:

1. Clone your target repo:

```bash
git clone https://github.com/<you>/what-do-i-become.git
cd what-do-i-become
```

2. Configure `src/.env`:

```bash
cp src/.env.example src/.env
nano src/.env
```

Set at minimum:

- `WDIB_GIT_REMOTE=origin`
- `WDIB_GIT_REMOTE_URL=git@github.com:<you>/what-do-i-become.git`
- `WDIB_LLM_PROVIDER=openai`
- `OPENAI_API_KEY=...`

For the GitHub credential model, prefer a **repo deploy key** (below) so each device has access to only one repository and can be revoked instantly.

### Provision a device (new hardware or existing OS)

Use this flow for both:

- Blank SD card / new hardware: flash Raspberry Pi OS first, then continue at step 1.
- Existing device with OS already installed: start at step 1.

1. Ensure system dependencies are installed (including Python):

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip git i2c-tools
python3 --version
git --version
```

2. Clone the repo onto the device:

```bash
git clone https://github.com/<you>/what-do-i-become.git
cd what-do-i-become
```

3. Add GitHub credentials for this device (recommended: repo deploy key with write access).

Important: you do **not** copy a secret from GitHub to the device in this flow. You generate a keypair on the device, then add only the public key to GitHub.

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -f ~/.ssh/wdib_repo -C "wdib-$(hostname)-$(date +%F)" -N ""
cat ~/.ssh/wdib_repo.pub
```

In GitHub (target repo):

1. Go to `Settings` -> `Deploy keys` -> `Add deploy key`.
2. Title: `wdib-<hostname>` (or similar).
3. Key: paste `~/.ssh/wdib_repo.pub`.
4. Enable `Allow write access`.

Pin this repo to that key on the device:

```bash
cat >> ~/.ssh/config <<'EOF'
Host github-wdib
  HostName github.com
  User git
  IdentityFile ~/.ssh/wdib_repo
  IdentitiesOnly yes
EOF

git remote set-url origin git@github-wdib:<you>/what-do-i-become.git
```

If you set `WDIB_GIT_REMOTE_URL` in `src/.env`, set it to the same host alias so `setup.sh` keeps the same remote URL:

```dotenv
WDIB_GIT_REMOTE_URL=git@github-wdib:<you>/what-do-i-become.git
```

Sanity-check auth before setup:

```bash
ssh -T git@github-wdib
git push --dry-run origin HEAD
```

To revoke this device later, delete the deploy key in the repo's `Settings` -> `Deploy keys`. The device immediately loses push access to this repo.

Note: deploy keys are repo-scoped (good), but not path-scoped within a repo.

4. Run setup:

```bash
chmod +x src/setup.sh
./src/setup.sh
```

5. Ensure cron has a daily run entry.
`setup.sh` usually adds this automatically, but if you need to add it manually, use:

```bash
(crontab -l 2>/dev/null; echo "0 9 * * * cd /path/to/what-do-i-become/src && ./run.sh >> /path/to/what-do-i-become/cron.log 2>&1") | crontab -
```

6. Run the first wake-up manually and verify:

```bash
./src/run.sh
git remote -v
crontab -l
```

Verify that:

- new files appear in `devices/<uuid>/`
- the device can push commits to your target repo

### Terminate a device (operator intervention)

Use this when a device is stuck, unreachable, or intentionally decommissioned. Termination is logged by a human-authored git commit.

1. On the hardware, stop future runs and decommission it (remove cron entry, power off, then wipe or repurpose):

```bash
(crontab -l 2>/dev/null | grep -v "src/run.sh"; true) | crontab -
sudo shutdown -h now
```

2. In the repo, remove the device state and commit the termination yourself:

```bash
UUID="<device-uuid>"
git rm -r "devices/${UUID}"
git commit -m "Terminate ${UUID:0:8} by operator ($(date +%F))" \
  -m "Reason: device decommissioned or stuck state; manual retirement."
git push
```

This keeps `Live Devices` accurate and provides an explicit operator audit trail.

### Self-terminate a device

If you want the device to retire itself, write the directive into its notes so it is part of persistent context:

`devices/<uuid>/notes.md`

```markdown
Operator directive: self-terminate this device.

Requirements:
1. Write a final session summary explaining termination reason.
2. Do not request new parts.
3. Disable your daily cron entry that runs `src/run.sh`.
4. End by shutting down the machine.
```

For immediate execution on the next run, also place a one-off instruction in `devices/<uuid>/human_message.txt`.
