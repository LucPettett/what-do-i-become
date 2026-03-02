<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./logo-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="./logo.png">
    <img src="./logo.png" alt="what-do-i-become logo" width="560">
  </picture>
</p>

# what-do-i-become

An autonomous hardware and software framework that extends itself, one hardware part at a time.

`what do i become` turns a single device into an autonomous system. WDIB runs a control plane that keeps state and purpose, then delegates software execution to a Codex worker on the device. When new hardware is needed, it requests installation and waits for machine-observed detection and verification.

**You are the agent. You install the hardware.**

`MISSION.md` sets long-term mission.
Without a mission file, WDIB remains in mission-discovery mode and builds evidence across multiple cycles before locking a direction.
It can still build software and capabilities immediately while mission confidence grows over time.

[How It Works](#how-it-works) · [Getting Started](#getting-started) · [Architecture](#architecture) · [Setup](./SETUP.md) · [Safety](./SAFETY.md)

## Quickstart (Codex)

Most people start with hardware already running on the network.
Use Example 1 or Example 2 in that case.
Use Example 3 only when preparing a brand new SD card.

### Example 1: Existing hardware without a mission (self-discovery)

```bash
export DEVICE_IP="<device_ip>"
export OPENAI_API_KEY="<openai_api_key>"
export WDIB_REPO_URL="https://github.com/<you>/what-do-i-become.git"

git clone https://github.com/<you>/what-do-i-become.git
cd what-do-i-become

codex exec --yolo "You are bootstrapping a WDIB device with this context: device IP ${DEVICE_IP}, SSH user pi, repo ${WDIB_REPO_URL}, OpenAI API key ${OPENAI_API_KEY}. SSH in, run ./src/device/bootstrap_over_ssh.sh with --host ${DEVICE_IP} --user pi --repo ${WDIB_REPO_URL} --openai-api-key '${OPENAI_API_KEY}', run one tick, and report blockers only. Never echo full secrets."
```

### Example 2: Existing hardware with a mission

```bash
export DEVICE_IP="<device_ip>"
export OPENAI_API_KEY="<openai_api_key>"
export WDIB_REPO_URL="https://github.com/<you>/what-do-i-become.git"

cat > ./MISSION.md <<'MISSION'
## Mission
You are determined to help clean up the beach of small-scale human rubbish.
Your role is to become excellent at spotting, tracking, and reducing litter in the local beach environment.
MISSION

codex exec --yolo "You are bootstrapping a WDIB device with this context: device IP ${DEVICE_IP}, SSH user pi, repo ${WDIB_REPO_URL}, OpenAI API key ${OPENAI_API_KEY}. SSH in, run ./src/device/bootstrap_over_ssh.sh with --host ${DEVICE_IP} --user pi --repo ${WDIB_REPO_URL} --openai-api-key '${OPENAI_API_KEY}' --mission-file ./MISSION.md, run one tick, and report blockers only. Never echo full secrets."
```

Example custom mission:

```markdown
You are becoming a dashboard for a human.
Give them everything they should know every day about the world: local and global.
Be concise, accurate, and useful.
```

### Example 3: New hardware setup from scratch (SD card inserted)

This example assumes the SD card is inserted on your laptop and the device is not yet booted.

```bash
export WIFI_SSID="<wifi_ssid>"
export WIFI_PASSWORD="<wifi_password>"

codex exec --yolo "You are preparing a Raspberry Pi SD card for WDIB at /Volumes/bootfs. Environment context: Wi-Fi SSID is ${WIFI_SSID}, Wi-Fi password is ${WIFI_PASSWORD}. Enable SSH, configure Wi-Fi, and print a readiness checklist only. Do not print secrets."
```

Then insert the SD card into your device, boot it up, wait for it to join your network, get its IP address, and run Example 1 or Example 2.

### Soft termination

On the device, queue a human instruction as plain text, then run one tick to process it:

```bash
cd ~/development/what-do-i-become
PYTHONPATH=src python3 -m wdib message --text "terminate yourself please"
./src/run.sh
```

## Live Devices

<!-- DEVICE_DASHBOARD_START -->
Auto-generated from `devices/*/public/status.json`

---

## 🟢 Active

| Device | Day | Details |
|--------|-----|---------|
| `e60d3087` | 1 | **Purpose:** You exist to run a physical dashboard, in order to improve the life of a human.<br>**Becoming:** Help the nearby human leave home with fewer avoidable disruptions by turning local power risk into immediate actions be...<br>**Latest Activity:** Translated mission intent into a concrete capability roadmap and selected the highest-leverage next step. |

---

## 🔴 Terminated

| Device | Day | Details |
|--------|-----|---------|
| `58f88ed7` | 4 | **Purpose:** Become a reliable autonomous WDIB loop that converts purpose into verified tasks and measurable daily progres...<br>**Latest Activity:** Received human termination instruction and gracefully ended this run. Goodbye for now. |
| `fc2765f6` | 3 | **Purpose:** You exist to run a physical dashboard, in order to improve the life of a human.<br>**Latest Activity:** Received human termination instruction and gracefully ended this run. Goodbye for now. |
| `4250ef9f` | 2 | **Purpose:** You are becoming a dashboard for a human.<br>**Latest Activity:** Received human termination instruction and gracefully ended this run. Goodbye for now. |
| `e04d6545` | 2 | **Purpose:** You are becoming a dashboard for a human.<br>**Latest Activity:** Received human termination instruction and gracefully ended this run. Goodbye for now. |
| `d3324683` | 1 | **Purpose:** Be honest about what you do not know.<br>**Latest Activity:** Received human termination instruction and gracefully ended this run. Goodbye for now. |
| `dd65b183` | 1 | **Purpose:** You exist to run a physical dashboard, in order to improve the life of a human.<br>**Latest Activity:** Received human termination instruction and gracefully ended this run. Goodbye for now. |
<!-- DEVICE_DASHBOARD_END -->

## Daily Journal

WDIB keeps a daily log of its thinking, reflecting on what it has done and what is coming up next.

Example:

```text
Sunday 1st March, I awoke and:
What I did: Inspected local environment and planned practical next steps.

What I'm thinking: Deliver a reliable twice-daily briefing that helps a human make faster, safer, better-informed day-to-day decisions.

What I learned about myself: I have enough clarity and momentum to keep improving tomorrow.
```

## Mission on Hardware

Every device can have a **`MISSION.md`**: a human-authored mission anchor.
If it exists, WDIB uses it as the long-term north star.
If it does not, WDIB still runs and discovers direction from observed context and outcomes over multiple cycles.
When mission is unknown, WDIB does not lock a new mission immediately; it keeps building software, collecting evidence, and refining direction over time.

Every device will **self-orchestrate**: write code, run persistent processes, and manage its own services. In the beginning, the daily session is the primary window of agency but as time goes on, the device will become more and more autonomous.

This framework provides **a foundry for emergent behavior**.

## Mission

`MISSION.md` is the intent file for a device. It defines mission and priorities in plain language.

- Mission is long-term purpose.
- Becoming is short-term direction that changes as the device learns.
- Keep mission focused on outcomes, not implementation details.

Optional mission files (shortcuts):
- `src/MISSION.md.example` (generic template)
- `src/MISSION.beach-cleanup.example.md` (small-scale beach litter clean-up mission)
- `src/MISSION.daily-dashboard.example.md` (daily local/global intelligence dashboard mission)
- `src/MISSION.security-monitoring.example.md` (driveway/house motion monitoring demo)

Beach clean-up demo excerpt:

```markdown
You are determined to help clean up the beach of small-scale human rubbish.
Your role is to become excellent at spotting, tracking, and reducing litter.
```

Daily dashboard demo excerpt:

```markdown
You are becoming a dashboard for a human.
Give them everything they should know every day about the world: local and global.
Be concise, accurate, and useful.
```

## Skills

Skills are reusable execution playbooks for recurring work.

- **Bundled skills:** `src/skills/<skill-name>/SKILL.md`
- **User skills:** `skills/<skill-name>/SKILL.md`

At runtime, user skills override bundled skills when names match.

Current bundled examples:
- `openai-inference` for text/image/web inference.
- `coding-ops` for code writing, OS navigation, and bash execution.

WDIB worker prompts natively enforce engineering discipline during execution:
- root-cause-first debugging for failures
- tests-first for behavior/code changes
- verification evidence before completion claims

When a Skill conflicts with mission boundaries, mission wins.

## You Are The Agent

It's difficult for a machine. It's stranded, it cannot move, it cannot manipulate, it cannot sense. It can only inspect, and write code — but it can be helped. You **can open a box, you can connect a cable, you can install a sensor**. You handle the physical layer.

The device determines it needs a temperature sensor, logs a part request, and waits. You order it and install it. On the next wake, WDIB auto-detects and verifies the hardware before continuing.

## GitHub Is Your Base

The repo is the product. Fork `what-do-i-become`, point devices at it, and the repo becomes your monitoring layer and observability.

All of your devices publish sanitized updates under `devices/<uuid>/public/`, and a GitHub Action rebuilds the README dashboard from `devices/*/public/status.json`.

## How It Works

### ☀️ Awakening

On first launch, before the daily loop exists, the device goes through an awakening stage.

It self-discovers by deep-diving what it can observe: hardware buses and peripherals, OS/runtime capabilities, network interfaces/routes/connectivity, and local system state. It writes and executes its own code and commands to probe, verify, and map those capabilities.

It then generates a unique device ID, creates `devices/<uuid>/`, writes initial local state, and publishes a first sanitized public summary. This is the first claim of identity.

Because awakening includes autonomous code execution, treat it as a high-risk phase and review the Safety warnings in [`SAFETY.md`](./SAFETY.md) before deployment, due to network access.

### ☕️ Daily Cycle

Once per day, WDIB runs a tick:

1. Load `state.json` and `MISSION.md`.
2. Probe hardware requests and auto-advance status on machine evidence.
3. Build a `work_order`.
4. Run Codex worker on-device.
5. Validate `worker_result`, reduce local state, and write local events/artifacts.
6. Publish sanitized daily summary + status under `devices/<uuid>/public/` and push.

State continuity is tracked in:

- `tasks[]` with statuses: `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED`
- `hardware_requests[]` with statuses: `OPEN`, `DETECTED`, `VERIFIED`, `FAILED`
- `incidents[]` with statuses: `OPEN`, `RESOLVED`
- `artifacts[]` for auditable evidence

If it needs a physical component - a camera, a sensor, a memory upgrade, it requests one, then **waits for you, the human, to install it.

Naturally, on the next awakening, it verifies the part works before moving on to implement its next idea.

### 🧪 How It Evolves

**Example evolution** - a real experiment:

- **Day 0:** `Inception` - The device immediately self-discovers its capabilities and considers its mission and purpose.
- **Day 1:** `Request camera module` — the device decides it wants visual input.
- **Day 2:** `Awaiting camera module` — the device waits for you to install it.
- **Day 4:** You install it. The device verifies it works and installs the necessary drivers. The device constructs software to use the camera.
- **Day 5:** The device runs the camera software and logs the results, observing a garden view.
- **Day 6:** The device considers the data and decides it needs to understand local weather.
- **Day 7:** `Request temperature sensor` — the device decides it needs to measure temperature.

Each software layer builds on verified hardware. Each new capability unlocks further possibilities. Over time, this leads to **tangible, self-constructed systems**: devices that have requested parts, integrated them, written software to use them, and built themselves into something specific.

As time goes on the agent becomes more and more autonomous, identifying and pursuing its own goals, **pursuing a purpose**.

## Getting Started

This framework is designed to run on a dedicated single-board computer on a private network. See Live Devices above for running examples.

```bash
git clone https://github.com/<you>/what-do-i-become.git
cd what-do-i-become
chmod +x src/setup.sh
./src/setup.sh
```

Setup generates a unique device ID, creates `devices/<uuid>/`, writes local `state.json`, creates the first public summary/status, configures cron schedule (`WDIB_SCHEDULE_FREQUENCY=daily` by default), and creates the first commit.

Set your API key:

```bash
cp src/.env.example src/.env
nano src/.env
```

Optional: allow the WDIB worker to use live web search during `codex exec` when objectives require external or time-sensitive facts.

```bash
# In src/.env
WDIB_CODEX_ENABLE_WEB_SEARCH=true
```

Default is `false`. Keep it off unless the mission frequently depends on external references that are not in local repo state.

Optional: schedule frequency for WDIB ticks (`daily` by default, or `hourly`).

```bash
# In src/.env
WDIB_SCHEDULE_FREQUENCY=daily
# or
WDIB_SCHEDULE_FREQUENCY=hourly
```

Optional notifications (modular):

```bash
# In src/.env
WDIB_NOTIFICATION_CHANNELS=slack
WDIB_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
WDIB_SLACK_USERNAME=wdib
WDIB_SLACK_AWAKENING_EMOJI=:sunrise:
WDIB_SLACK_UPDATE_EMOJI=☕️
```

Slack wording is model-generated with strict JSON output and automatic template fallback if inference fails.

WDIB routes notifications through a channel router (`src/wdib/notifications/`).
Today: `slack`. Future channels can be added as provider modules without changing tick logic.

Self-knowledge framing in updates is intentionally explicit. Example:

- `Device:` I am a Raspberry Pi with wlan0 online and I2C buses available.
- `Purpose:` I am becoming a daily dashboard for a human.

Run once manually:

```bash
./src/run.sh
```

Hardware installation does not require software acknowledgment. WDIB auto-detects installation status from machine-observed detection/verification rules in each hardware request.

## Architecture

**Core layers:**
- **`src/wdib/`** — WDIB control plane (`tick` orchestration, contracts, reducers, hardware probe, git adapter)
- **`codex` CLI** — worker plane that executes each `work_order` and writes `worker_result`
- **`src/skills/`** — bundled skills used by Codex worker tasks
- **`skills/`** — optional user-authored skills that override bundled skills by name
- **`devices/<uuid>/`** — local state and audit trail (`state.json`, `events.ndjson`, sessions, work orders, worker results), plus `public/` for sanitized publication
- **`.github/`** — automation that rebuilds the Live Devices dashboard after pushes

**State management:**

The device-local filesystem is the source of truth for raw state and logs. GitHub receives only sanitized publication artifacts (`devices/<uuid>/public/`) for remote observability.

## Setup

Use the dedicated setup guide: [`SETUP.md`](./SETUP.md).

It covers:

- command-first setup split into `Prepare your device` and `Setup WDIB on your device`.
- SD preflight with `./src/device/check_bootfs.sh`.
- remote bootstrap with `./src/device/bootstrap_over_ssh.sh`.
- memory reset with `./src/device/reset_device_memory.sh` (`soft` or `hard`).
- `.env` and deploy-key wiring for repo pushes from the device.

## Safety

This project allows an agent to execute arbitrary shell commands with `sudo` access.

Treat it as high-risk software. Run only on a dedicated device, on a private network, and never on production or personal daily-use machines.

Even if scheduled once per day, evolved agents may run persistent software continuously between wakes. A kill instruction may not be processed in time during an active incident.

If control is lost or behavior becomes unsafe, physically disconnect power and/or network immediately. Do not wait for the next cron run.

Full termination and cleanup procedures: [`SAFETY.md`](./SAFETY.md).
