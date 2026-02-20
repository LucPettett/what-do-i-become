<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="./logo.png">
    <img src="./logo.png" alt="what-do-i-become logo" width="560">
  </picture>
</p>

# what-do-i-become

A self-construction framework for hardware that wakes up, explores itself, and asks you to build it into something. An LLM agent runs daily on dedicated devices, inspecting what hardware exists, writing code to use it, and requesting specific parts when needed.

[How It Works](#how-it-works) · [Getting Started](#getting-started) · [Architecture](#architecture) · [Setup](./SETUP.md) · [Safety](#safety)

---

## Live Devices

Devices running right now. Auto-generated from `devices/*/device.yaml`.

<!-- DEVICE_DASHBOARD_START -->
| Device | Awoke | Day | Becoming | Status |
| --- | --- | ---: | --- | --- |
<!-- No devices yet. Add your first device using the setup guide. -->
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

Example: the device determines it needs a temperature sensor, logs a part request, and waits. You order it, install it, and leave a note in `human_message.txt`. Next morning, the device tests the sensor and continues.

## GitHub Is Your Base

The repo is the product. Fork `what-do-i-become`, point devices at it, and the repo becomes your database, monitoring layer, and oversight tool.

Every session is committed. Every part request is logged. Every decision is in version control.

Devices push only to `devices/<uuid>/`, and a GitHub Action rebuilds the README dashboard from `devices/*/device.yaml`.

## How It Works

### Daily Cycle

The device wakes once per day on a cron schedule. It loads its context — spirit, state, any message you left — and enters an agent loop where it can inspect hardware, run commands, write files, and reason about what to do next.

If it needs a physical part it doesn't have, it requests exactly one, then waits for you to install it. On the next run, it verifies the part works before moving on.

At the end of every session, the device writes a session log, updates `device.yaml`, and pushes to the repo. Then it sleeps until tomorrow.

That's the whole loop: wake, think, act, log, sleep.

### Growth Pattern

Your device begins in self-discovery: inspecting hardware, software, sensors, and constraints to form a working understanding of its current capabilities.

Then it enters a growth loop: expand capabilities, verify, build, repeat. Each run records evidence in git.

The `becoming` field in `device.yaml` starts empty and evolves as the device verifies new capabilities. Identity is not fixed—it keeps changing.

This can lead to tangible, self-constructed hardware systems: devices that have asked for parts, integrated them, verified them, and evolved into concrete physical builds over time.

## Getting Started

This framework is designed to run on a dedicated single-board computer on a private network. We recommend a Raspberry Pi. See Live Devices above for running examples.

```bash
git clone https://github.com/<you>/what-do-i-become.git
cd what-do-i-become
chmod +x src/setup.sh
./src/setup.sh
```

Setup generates a unique device ID, creates `devices/<uuid>/`, discovers hardware, writes the initial `device.yaml` with `awoke` set to today and `becoming` empty, configures daily cron at 09:00, and creates the first commit.

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

## Architecture

**Three layers:**
- `src/`: runtime framework (agent loop, tools, memory, setup scripts, spirit prompt)
- `devices/<uuid>/`: per-device state and history written by the device itself
- `.github/`: automation that rebuilds the Live Devices dashboard after pushes

**State management:**

The repo is the control plane. State, identity evolution (`becoming`), and operational history all live in version control. Every session commits its changes, making the entire system auditable through git history.

## Setup

Use the dedicated setup guide: [`SETUP.md`](./SETUP.md).

It covers:

- `.env` configuration (`src/.env`) and required keys.
- `Add a device (fresh device / microSD first boot)` workflow.
- `Add a device (existing device / already running OS)` workflow.
- repo-scoped deploy key setup and revocation.
- verification checks and device termination procedures.

## Safety

These agents execute arbitrary shell commands with `sudo` access. Run this on a dedicated device on a private network, not on your daily machine, not on production infrastructure.
