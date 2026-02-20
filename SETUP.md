# Setup Guide

Use this guide to provision and operate devices for `what-do-i-become`.

## Prepare Your Repo

Do this once for your fork:

```bash
git clone https://github.com/<you>/what-do-i-become.git
cd what-do-i-become
cp src/.env.example src/.env
nano src/.env
```

Set at minimum:

- `WDIB_LLM_PROVIDER=openai`
- `OPENAI_API_KEY=...`

Optional git settings:

- `WDIB_GIT_REMOTE=origin` (default)
- `WDIB_GIT_BRANCH=` (optional explicit push target)
- `WDIB_GIT_AUTO_PUSH=true` (default)
- `WDIB_GIT_REMOTE_URL=...` (use if you want `setup.sh` to force a specific remote)
- `WDIB_GIT_USER_NAME=...` and `WDIB_GIT_USER_EMAIL=...` (optional local identity override)

## Add a device (fresh device / microSD first boot)

Use this for Raspberry Pi-class devices when the microSD card is mounted on your laptop before first boot.

Goal: pre-provision Wi-Fi and Git auth so the device can push without an initial manual SSH setup session.

Requirements:

- boot partition mounted locally (example macOS path: `/Volumes/bootfs`)
- image supports first-boot files such as `wpa_supplicant.conf` and optionally `user-data` (cloud-init)

### Prompt Template (Codex/Claude)

```text
The microSD card is mounted at /Volumes/bootfs.

Please pre-provision it for what-do-i-become:
1. Update /Volumes/bootfs/wpa_supplicant.conf with SSID "<WIFI_SSID>" and password "<WIFI_PASSWORD>".
2. Ensure SSH is enabled (create /Volumes/bootfs/ssh if missing). For SSH your root password is "<ROOT_PASSWORD>".
3. Generate an ed25519 keypair dedicated to this device/repo.
4. Backup /Volumes/bootfs/user-data, then update it so first boot writes:
   - /home/pi/.ssh/wdib_repo (private key, 0600)
   - /home/pi/.ssh/wdib_repo.pub (public key, 0644)
   - /home/pi/.ssh/config with:
     Host github-wdib
       HostName github.com
       User git
       IdentityFile ~/.ssh/wdib_repo
       IdentitiesOnly yes
5. In first-boot commands, set ownership/permissions, add github.com to known_hosts, and add git URL rewrite:
   https://github.com/<GITHUB_OWNER>/ -> git@github-wdib:<GITHUB_OWNER>/
6. Print only the public key and fingerprint, list changed files, and run sync.

Do not print private keys in output and do not write credentials into this repository.
```

### After the patch

1. In GitHub (`<you>/what-do-i-become`), open `Settings` -> `Deploy keys` -> `Add deploy key`.
2. Paste the generated public key.
3. Enable `Allow write access`.
4. Boot the device.
5. If clone/setup was not automated in `user-data`, continue with `Add a device (existing device)` below.

Revocation: delete that deploy key to immediately stop pushes from that device.

## Add a device (existing device / already running OS)

Use this when the device is already booted and reachable by SSH or local console.

1. Install dependencies:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip git i2c-tools
python3 --version
git --version
```

2. Clone repo:

```bash
git clone https://github.com/<you>/what-do-i-become.git
cd what-do-i-become
```

3. Create a device-specific deploy key on the device:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -f ~/.ssh/wdib_repo -C "wdib-$(hostname)-$(date +%F)" -N ""
cat ~/.ssh/wdib_repo.pub
```

4. In GitHub (`<you>/what-do-i-become`), add deploy key with write access:

1. `Settings` -> `Deploy keys` -> `Add deploy key`
2. paste `~/.ssh/wdib_repo.pub`
3. enable `Allow write access`

5. Pin this repo to that key:

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

If you use `WDIB_GIT_REMOTE_URL` in `src/.env`, match the same alias:

```dotenv
WDIB_GIT_REMOTE_URL=git@github-wdib:<you>/what-do-i-become.git
```

6. Run setup and first wake-up:

```bash
chmod +x src/setup.sh
./src/setup.sh
./src/run.sh
git remote -v
crontab -l
```

Verify:

- new files appear in `devices/<uuid>/`
- push succeeds to your target repo

Revocation: delete this deploy key in repo settings to immediately block access.

## Terminate a device (operator intervention)

Use this when a device is stuck, unreachable, or intentionally decommissioned.

1. On hardware, stop future runs and power down:

```bash
(crontab -l 2>/dev/null | grep -v "src/run.sh"; true) | crontab -
sudo shutdown -h now
```

2. In repo, remove device state and commit termination:

```bash
UUID="<device-uuid>"
git rm -r "devices/${UUID}"
git commit -m "Terminate ${UUID:0:8} by operator ($(date +%F))" \
  -m "Reason: device decommissioned or stuck state; manual retirement."
git push
```

## Self-terminate a device

Warning: self-termination is best-effort. If the agent hangs, loses network, or cannot complete shutdown steps, you may still need a physical power disconnect and manual cleanup.

If you want the device to retire itself, place a directive in:

- `devices/<uuid>/notes.md`

Example:

```markdown
Operator directive: self-terminate this device.

Requirements:
1. Write a final session summary explaining termination reason.
2. Do not request new parts.
3. Disable your daily cron entry that runs `src/run.sh`.
4. End by shutting down the machine.
```

For immediate execution on next run, also write a one-off instruction in:

- `devices/<uuid>/human_message.txt`

## Important cleanup after termination

Do these even if self-termination reports success:

1. Remove GitHub repo permissions for that device (delete its deploy key in `Settings` -> `Deploy keys`).
2. Rotate network credentials used by the retired device (change Wi-Fi password and reconnect active devices).
3. Rotate inference API keys that were present on that device (for example `OPENAI_API_KEY`).
