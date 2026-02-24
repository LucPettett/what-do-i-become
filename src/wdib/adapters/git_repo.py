"""Git commit/push adapter for per-device WDIB traces."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from ..env import env_bool
from ..paths import PROJECT_ROOT


def commit_device_changes(device_id: str, day: int, status: str) -> dict[str, Any]:
    if env_bool("WDIB_SKIP_GIT_COMMIT", default=False):
        return {
            "committed": False,
            "pushed": False,
            "message": "Skipped git commit because WDIB_SKIP_GIT_COMMIT=true.",
        }

    device_rel = f"devices/{device_id}"
    short_id = device_id[:8]

    remote = (os.environ.get("WDIB_GIT_REMOTE") or "origin").strip() or "origin"
    branch = (os.environ.get("WDIB_GIT_BRANCH") or "").strip()
    auto_push = env_bool("WDIB_GIT_AUTO_PUSH", default=True)
    git_user_name = (os.environ.get("WDIB_GIT_USER_NAME") or "").strip()
    git_user_email = (os.environ.get("WDIB_GIT_USER_EMAIL") or "").strip()

    os.chdir(PROJECT_ROOT)

    if git_user_name:
        subprocess.run(["git", "config", "user.name", git_user_name], check=False)
    if git_user_email:
        subprocess.run(["git", "config", "user.email", git_user_email], check=False)

    subprocess.run(["git", "add", device_rel], check=True)

    changed = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--", device_rel],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not changed:
        return {"committed": False, "pushed": False, "message": "No device changes to commit."}

    message = f"{short_id} day {day:03d} - {status}"
    subprocess.run(["git", "commit", "-m", message, "--", device_rel], check=True)

    if not auto_push:
        return {"committed": True, "pushed": False, "message": message}

    remote_exists = subprocess.run(
        ["git", "remote", "get-url", remote],
        capture_output=True,
        text=True,
    )
    if remote_exists.returncode != 0:
        return {
            "committed": True,
            "pushed": False,
            "message": f"{message} (remote '{remote}' not configured)",
        }

    push_cmd = ["git", "push", remote]
    if branch:
        push_cmd.append(f"HEAD:{branch}")

    pushed = subprocess.run(push_cmd, capture_output=True, text=True)
    if pushed.returncode != 0:
        return {
            "committed": True,
            "pushed": False,
            "message": f"{message} (push failed: {(pushed.stderr or '').strip()[:200]})",
        }

    return {"committed": True, "pushed": True, "message": message}
