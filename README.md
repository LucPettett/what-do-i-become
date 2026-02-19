<p align="center">
  <img src="./logo.png" alt="what-do-i-become logo" width="340" />
</p>

# what-do-i-become

A self-construction framework for hardware systems that learn what they are, decide what they need, and request upgrades over time.

Human as an agent is a core design principle: the machine decides, and the human executes physical-world actions (buy/install/wire parts) and reports back.

This repo is the Raspberry Pi reference implementation of that framework.

[Quick Start](#quick-start) · [How It Works](#how-it-works) · [Safety](#safety)

## How It Works

This is not just "a Pi project." The Pi is the first host for a general hardware self-construction loop.

Once per day, a GPT-5 agent wakes up on the host machine, inspects itself, runs commands, writes files, and explores what it can do next.

When it needs a new capability (camera, sensor, microphone, storage, etc.), it requests one specific part. A human installs that part, and the agent verifies it before moving on.

Every run is saved as YAML and committed, so the project keeps a day-by-day behavior log.

```text
cron (09:00)
     |
     v
./run.sh
     |
     v
load context (state.yaml, notes.md, human_message.txt, hardware checks)
     |
     v
GPT-5 agent loop
  - inspect itself
  - run commands
  - write files
  - decide next capability
     |
     +--> needs new hardware?
     |      request exactly one part
     |      wait for human install
     |      verify on next run
     |
     v
write session log (sessions/day_###_YYYY-MM-DD.yaml)
git add -A && git commit && git push
     |
     v
sleep until next day
```

## Quick Start

1. Flash Raspberry Pi OS with [Raspberry Pi Imager](https://www.raspberrypi.com/software/), enable SSH, and configure WiFi.
2. SSH into the Pi.
3. Clone this repo and run setup.

```bash
ssh <username>@<pi-ip>
git clone git@github.com:<you>/<your-repo>.git
cd <your-repo>/_experiments/luc-pi
chmod +x setup.sh
./setup.sh
```

`setup.sh` installs dependencies, enables common Pi interfaces, creates `sessions/`, copies `.env`, and installs a daily cron run at `09:00`.

4. Set your API key.

```bash
cp .env.example .env   # if needed
nano .env
```

```env
OPENAI_API_KEY=...
```

5. Run once manually to confirm everything works.

```bash
./run.sh
```

## Hardware + Accounts

- Raspberry Pi with WiFi (Pi 5 recommended)
- microSD card (32GB+ recommended)
- Correct Pi power supply
- OpenAI API key
- Git remote the Pi can push to (GitHub or equivalent)

## Git Flow

If this directory is not yet connected to your remote:

```bash
git remote add origin git@github.com:<you>/<your-repo>.git
git branch -M main
git push -u origin main
```

After each session, the agent attempts:

- `git add -A`
- `git commit -m "Day N (YYYY-MM-DD) - <PHASE>"`
- `git push`

If push fails, it retries in later sessions.

## Human Input

Leave a one-off message for the next wake-up:

```bash
echo "I installed the camera on CSI." > human_message.txt
```

The file is consumed at session start, then deleted.

## Project Layout

```text
luc-pi/
├── README.md
├── .env.example
├── .gitignore
├── setup.sh
├── run.sh
├── agent.py
├── tools.py
├── memory.py
├── state.yaml          # auto-generated after first run
├── notes.md            # auto-generated when notes are saved
├── human_message.txt   # optional; consumed then deleted
└── sessions/           # daily YAML logs
```

The repo stays intentionally flat: code and runtime state live side by side for easier inspection.

## Safety

This agent executes shell commands and may run `sudo`. Treat this Pi as an isolated experiment box, not production infrastructure.

## Inspiration

- [OpenClaw](https://github.com/openclaw/openclaw)
- [Armin Ronacher: Building a Self-Expanding Raspberry Pi](https://lucumr.pocoo.org/2026/1/31/pi/)
