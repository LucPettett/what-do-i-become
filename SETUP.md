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
- `devices/<uuid>/wdib.log` is created and appends each run (including API/LLM errors)
- push succeeds to your target repo

## Skills

Bundled skills live in `src/skills/`.

Add your own skills in `skills/<name>/SKILL.md`. User skills are loaded with higher precedence than bundled skills, so matching names override bundled behavior. No skill feature flags are required.

Revocation: delete this deploy key in repo settings to immediately block access.

## Safety and termination

All safety policy and termination procedures are documented in [`SAFETY.md`](./SAFETY.md).
