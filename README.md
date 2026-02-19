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
- `WDIB_GIT_REMOTE_URL` (setup can add remote if missing)
- `WDIB_GIT_USER_NAME`, `WDIB_GIT_USER_EMAIL` (optional local git identity override)

## Directory Layout

`src/` is the framework — agent, tools, memory, setup, and spirit. `devices/` is per-device state — one subdirectory per UUID containing `device.yaml`, session logs, notes, and any human messages. `.github/` rebuilds the README dashboard on push.

## Safety

These agents execute shell commands and may run `sudo`. Run this on a dedicated device on a private network, not on your daily machine, not on production infrastructure.
