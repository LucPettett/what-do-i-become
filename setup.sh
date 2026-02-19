#!/usr/bin/env bash
# First-time setup for what-do-i-become.
# Run once on a fresh Raspberry Pi:  chmod +x setup.sh && ./setup.sh

set -e
cd "$(dirname "$0")"

echo "══════════════════════════════════════════════════════════"
echo "  what-do-i-become — First-Time Setup"
echo "══════════════════════════════════════════════════════════"

# System packages
echo ""
echo "→ Installing system packages…"
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip git i2c-tools

# Python packages
echo ""
echo "→ Installing Python packages…"
pip3 install --break-system-packages openai pyyaml 2>/dev/null \
  || pip3 install openai pyyaml

# Enable common interfaces (non-interactive)
echo ""
echo "→ Enabling I2C and camera interfaces…"
sudo raspi-config nonint do_i2c 0 2>/dev/null || echo "  (skipped — not on Pi or already enabled)"
sudo raspi-config nonint do_camera 0 2>/dev/null || echo "  (skipped — not on Pi or already enabled)"

# Directory structure
echo ""
echo "→ Creating directories…"
mkdir -p sessions

# .env from template
if [ ! -f .env ]; then
    cp .env.example .env
    echo "→ Created .env from template — edit it to add your OpenAI API key"
else
    echo "→ .env already exists — skipping"
fi

# Make scripts executable
chmod +x run.sh

# Git init
if [ ! -d .git ]; then
    echo ""
    echo "→ Initialising git repository…"
    git init
    git add -A
    git commit -m "Day 0 — what-do-i-become is born"
    echo ""
    echo "  ⚠️  Add a remote and push:"
    echo "    git remote add origin <your-repo-url>"
    echo "    git branch -M main"
    echo "    git push -u origin main"
else
    echo "→ Git repo already initialised"
fi

# Cron job
echo ""
echo "→ Setting up daily cron job (9:00 AM)…"
AGENT_DIR="$(pwd)"
CRON_CMD="0 9 * * * cd ${AGENT_DIR} && ./run.sh >> cron.log 2>&1"

# Avoid duplicates
( crontab -l 2>/dev/null | grep -v "what-do-i-become\|run\.sh" ; echo "$CRON_CMD" ) | crontab -
echo "  Installed: $CRON_CMD"

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Edit .env → add your OPENAI_API_KEY"
echo "    2. Add git remote → git remote add origin <url>"
echo "    3. Push → git push -u origin main"
echo "    4. Test manually → ./run.sh"
echo "    5. The agent will wake daily at 9 AM"
echo ""
echo "  Optional: drop a human_message.txt file in this"
echo "  directory to send the agent a message next session."
echo "══════════════════════════════════════════════════════════"
