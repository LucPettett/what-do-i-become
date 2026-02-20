<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./logo-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="./logo.png">
    <img src="./logo.png" alt="what-do-i-become logo" width="560">
  </picture>
</p>

# what-do-i-become

An autonomous hardware & software framework that extends itself, one hardware part at a time.

`what do i become` is a framework that turns a single device into an autonomous agentic system. An LLM agent inspects what hardware it has availabile, designs and writes code to execute, and **askes you to install new hardware**.

**You are the agent. You install the hardware.**

With no configuration: `what-do-i-become` could become anything.

With a Spirit file, `what-do-i-become` becomes whatever you want it to become.

As it evolves, WDOB will eventually create and construct it's own software, becoming more and more autonomous, serving a single purpose.

[How It Works](#how-it-works) · [Getting Started](#getting-started) · [Architecture](#architecture) · [Setup](./SETUP.md) · [Safety](./SAFETY.md)

---

## Live Devices

Devices running right now. Auto-generated from `devices/*/device.yaml`.

<!-- DEVICE_DASHBOARD_START -->
| Device | Awoke | Day | Becoming | Status |
| --- | --- | ---: | --- | --- |
<!-- No devices yet. Add your first device using the setup guide. -->
<!-- DEVICE_DASHBOARD_END -->

## Hardware with a spirit

Every device has a **`SPIRIT.md`** — the founding instructions for behavior and direction. This file is human-authored, but is also not required (empty spirits are fine). Regardless, spirit or no spirit, the device will evolve into something.

- **A `SPIRIT.md` may be given.**
- **A `becoming` is discovered.**

Every device will **self-orchestrate**: write code, run persistent processes, and manage its own services. In the beginning, the daily session is the primary window of agency but as time goes on, the device will become more and more autonomous.

This framework provides **a foundry for emergent behavior**.

## You Are The Agent

It's difficult for a machine. It's stranded, it cannot move, it cannot manipulate, it cannot sense. It can only inspect, and write code — but it can be helped. You **can open a box, you can connect a cable, you can install a sensor**. You handle the physical layer.

The device determines it needs a temperature sensor, logs a part request, and waits. You order it, install it, and leave a note in `human_message.txt`. Next morning, the device tests the sensor and continues.

## GitHub Is Your Base

The repo is the product. Fork `what-do-i-become`, point devices at it, and the repo becomes your monitoring layer and observability.

All of your devices will commit to fork of this repo, under  `devices/<uuid>/`, and a GitHub Action rebuilds the README dashboard from `devices/*/device.yaml`.

## How It Works

### Daily Cycle

The device wakes once per day on a cron schedule. It loads its context — **spirit, state, any message you left** — and enters an agent loop where it can inspect hardware, run commands, write files, and reason about what to do next.

If it needs a physical part it doesn't have, it **requests exactly one**, then waits for you to install it. On the next run, it verifies the part works before moving on.

At the end of every session, the device writes a **session log**, updates `device.yaml`, and pushes to the repo. Then it sleeps until tomorrow.

### How It Evolves

**Example evolution** — a real expirement:

- **Day 0:** `Inception` - The device immediately self discovers its capabilities and considers it's spirit and purpose.
- **Day 1:** `Request camera module` — the device decides it wants visual input.
- **Day 2:** `Awaiting camera module` — the device waits for you to install it.
- **Day 4:** You install it. The device verifies it works and installs the necessary drivers. The device constructs software to use the camera.
- **Day 5:** The device runs the camera software and logs the results, observing a garden view.
- **Day 6:** The device considers the data and decides it needs to understand it's weather. 
- **Day 7:** `Request temperature sensor` — the device decides it needs to measure temperature.

Each software layer builds on verified hardware. Each new capability unlocks further possibilities. Over time, this leads to **tangible, self-constructed systems**: devices that have requested parts, integrated them, written software to use them, and built themselves into something specific.

As time goes on the agent becomes more and more autonomous, identifing and pursuing it's own goals, **pursuing a purpose**.

## Getting Started

This framework is designed to run on a dedicated single-board computer on a private network. See Live Devices above for running examples.

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
- **`src/`** — runtime framework (agent loop, tools, memory, setup scripts, spirit prompt)
- **`devices/<uuid>/`** — per-device state and history, written by the device itself
- **`.github/`** — automation that rebuilds the Live Devices dashboard after pushes

**State management:**

The repo is the **single source of truth**. State, identity evolution (`becoming`), and operational history all live in version control. Every session commits its changes, making the entire system **auditable through git history**.

## Setup

Use the dedicated setup guide: [`SETUP.md`](./SETUP.md).

It covers:

- `.env` configuration (`src/.env`) and required keys.
- `Add a device (fresh device / microSD first boot)` workflow.
- `Add a device (existing device / already running OS)` workflow.
- repo-scoped deploy key setup and revocation.
- verification checks for setup and first wake-up.

## Safety

Safety and termination guidance lives in [`SAFETY.md`](./SAFETY.md).
