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

`spirit.md` sets long-term mission.
Without a spirit file, WDIB self-discovers its direction from observed reality and daily work.
Either way, each cycle updates its near-term becoming and continues building toward a concrete purpose.

[How It Works](#how-it-works) · [Getting Started](#getting-started) · [Architecture](#architecture) · [Setup](./SETUP.md) · [Safety](./SAFETY.md)

## Quickstart (Codex)

Most people start with hardware already running on the network.
Use Example 1 or Example 2 in that case.
Use Example 3 only when preparing a brand new SD card.

### Example 1: Existing hardware without a spirit (self-discovery)

```bash
export DEVICE_IP="<device_ip>"
export OPENAI_API_KEY="<openai_api_key>"
export WDIB_REPO_URL="https://github.com/<you>/what-do-i-become.git"

git clone https://github.com/<you>/what-do-i-become.git
cd what-do-i-become

codex exec --yolo "You are bootstrapping a WDIB device with this context: device IP ${DEVICE_IP}, SSH user pi, repo ${WDIB_REPO_URL}, OpenAI API key ${OPENAI_API_KEY}. SSH in, run ./src/device/bootstrap_over_ssh.sh with --host ${DEVICE_IP} --user pi --repo ${WDIB_REPO_URL} --openai-api-key '${OPENAI_API_KEY}', run one tick, and report blockers only. Never echo full secrets."
```

### Example 2: Existing hardware with a spirit

```bash
export DEVICE_IP="<device_ip>"
export OPENAI_API_KEY="<openai_api_key>"
export WDIB_REPO_URL="https://github.com/<you>/what-do-i-become.git"

cat > ./spirit.md <<'SPIRIT'
## Mission
You are determined to help clean up the beach of small-scale human rubbish.
Your role is to become excellent at spotting, tracking, and reducing litter in the local beach environment.
SPIRIT

codex exec --yolo "You are bootstrapping a WDIB device with this context: device IP ${DEVICE_IP}, SSH user pi, repo ${WDIB_REPO_URL}, OpenAI API key ${OPENAI_API_KEY}. SSH in, run ./src/device/bootstrap_over_ssh.sh with --host ${DEVICE_IP} --user pi --repo ${WDIB_REPO_URL} --openai-api-key '${OPENAI_API_KEY}' --spirit-file ./spirit.md, run one tick, and report blockers only. Never echo full secrets."
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

### Human software command (graceful terminate)

On the device, queue a human instruction as plain text, then run one tick to process it:

```bash
cd ~/development/what-do-i-become
PYTHONPATH=src python3 -m wdib message --text "terminate and say goodbye"
./src/run.sh
```

---

## Journal Output

Slack updates are written as a daily journal with three sections:

- **What I did** (concrete engineering actions from this cycle)
- **What I'm thinking** (mission and self-reflection tied to becoming)
- **What's next** (the next practical tasks)

Message phases are distinct:

- **Awakening**: first-run voice and first mission framing
- **Update**: normal daily engineering journal
- **Terminate**: reflective, graceful shutdown message

The live dashboard still comes from `devices/*/public/status.json`, while Slack carries the more human daily narrative.

## Live Devices

Devices running right now. Auto-generated from `devices/*/public/status.json`.

<!-- DEVICE_DASHBOARD_START -->
| Device | Awoke | Day | Purpose | Becoming | Recent Activity | Status |
| --- | --- | ---: | --- | --- | --- | --- |
| `4250ef9f` | 2026-03-01 | 1 | You are becoming a dashboard for a human. | Deliver a reliable twice-daily briefing that helps a human make faster, safer, better-informed day-to-day decisions. | Inspected local environment and planned practical next steps. | ACTIVE |
| `58f88ed7` | 2026-03-01 | 4 | Become a reliable autonomous WDIB loop that converts purpose into verified tasks and measurable daily progres... | Gracefully conclude this mission run and hand over cleanly. | Received human termination instruction and gracefully ended this run. Goodbye for now. | TERMINATED |
<!-- DEVICE_DASHBOARD_END -->

## Spirit on Hardware

Every device can have a **`spirit.md`**: a human-authored mission anchor.
If it exists, WDIB uses it as the long-term north star.
If it does not, WDIB still runs and discovers direction from observed context and outcomes.

Every device will **self-orchestrate**: write code, run persistent processes, and manage its own services. In the beginning, the daily session is the primary window of agency but as time goes on, the device will become more and more autonomous.

This framework provides **a foundry for emergent behavior**.

## Spirit

`spirit.md` is the intent file for a device. It defines mission and priorities in plain language.

- Spirit is long-term purpose.
- Becoming is short-term direction that changes as the device learns.
- Keep spirit focused on outcomes, not implementation details.

Optional Spirit files (shortcuts):
- `src/SPIRIT.md.example` (generic template)
- `src/SPIRIT.beach-cleanup.example.md` (small-scale beach litter clean-up mission)
- `src/SPIRIT.daily-dashboard.example.md` (daily local/global intelligence dashboard mission)
- `src/SPIRIT.security-monitoring.example.md` (driveway/house motion monitoring demo)

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

When a Skill conflicts with Spirit boundaries, Spirit wins.

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

1. Load `state.json` and `SPIRIT.md`.
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

- **Day 0:** `Inception` - The device immediately self-discovers its capabilities and considers its spirit and purpose.
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

Setup generates a unique device ID, creates `devices/<uuid>/`, writes local `state.json`, creates the first public summary/status, configures daily cron at 09:00, and creates the first commit.

Set your API key:

```bash
cp src/.env.example src/.env
nano src/.env
```

Optional notifications (modular):

```bash
# In src/.env
WDIB_NOTIFICATION_CHANNELS=slack
WDIB_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
WDIB_SLACK_USERNAME=wdib
WDIB_SLACK_AWAKENING_EMOJI=:sunrise:
WDIB_SLACK_UPDATE_EMOJI=☕️
WDIB_SLACK_MESSAGE_STYLE=human
```

WDIB routes notifications through a channel router (`src/wdib/notifications/`).
Today: `slack`. Future channels can be added as provider modules without changing tick logic.

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
