"""Slack Incoming Webhook adapter for WDIB notifications."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any
from urllib import error, request


def _webhook_url() -> str:
    return str(os.environ.get("WDIB_SLACK_WEBHOOK_URL") or "").strip()


def is_configured() -> bool:
    return bool(_webhook_url())


def _timeout_seconds() -> float:
    raw = str(os.environ.get("WDIB_SLACK_TIMEOUT_SECONDS") or "").strip()
    if not raw:
        return 8.0
    try:
        value = float(raw)
    except ValueError:
        return 8.0
    if value <= 0:
        return 8.0
    return value


def _build_cycle_text(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> str:
    short_id = str(status_payload.get("device_id_short") or "-")
    day = int(status_payload.get("day") or 0)
    status = str(status_payload.get("status") or "UNKNOWN")
    worker_status = str(status_payload.get("worker_status") or "UNKNOWN")
    cycle_id = str(status_payload.get("cycle_id") or "-")
    becoming = str(status_payload.get("becoming") or "").strip()
    pushed = bool(git_info.get("pushed"))
    git_mark = "yes" if pushed else "no"

    lines = [
        f"*WDIB Daily Summary* ({run_date})",
        f"- Device: `{short_id}`",
        f"- Day: `{day:03d}`",
        f"- Status: `{status}` | Worker: `{worker_status}`",
        f"- Cycle: `{cycle_id}`",
    ]
    if becoming:
        lines.append(f"- Becoming: {becoming}")
    lines.extend(
        [
            f"- Pushed to GitHub: `{git_mark}`",
            "- This update is sanitized; detailed logs remain on-device.",
        ]
    )
    return "\n".join(lines)


def _build_failure_text(device_id: str, cycle_id: str, day: int, ts: datetime) -> str:
    short_id = device_id[:8] if device_id else "-"
    run_date = ts.date().isoformat()
    return "\n".join(
        [
            f"*WDIB Cycle Failed* ({run_date})",
            f"- Device: `{short_id}`",
            f"- Day: `{int(day):03d}`",
            f"- Cycle: `{cycle_id}`",
            "- Check device-local logs for details.",
        ]
    )


def _post_text(text: str) -> dict[str, Any]:
    url = _webhook_url()
    if not url:
        return {"sent": False, "reason": "WDIB_SLACK_WEBHOOK_URL is not configured"}

    payload: dict[str, Any] = {"text": text}
    username = str(os.environ.get("WDIB_SLACK_USERNAME") or "").strip()
    icon_emoji = str(os.environ.get("WDIB_SLACK_ICON_EMOJI") or "").strip()
    if username:
        payload["username"] = username
    if icon_emoji:
        payload["icon_emoji"] = icon_emoji

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=_timeout_seconds()) as resp:  # noqa: S310
            status_code = int(getattr(resp, "status", 0) or 0)
            response_body = resp.read().decode("utf-8", errors="replace")
    except error.URLError as exc:
        return {"sent": False, "reason": f"webhook request failed: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"sent": False, "reason": f"webhook request failed: {exc}"}

    if status_code != 200:
        return {
            "sent": False,
            "reason": f"unexpected response status {status_code}",
            "status_code": status_code,
            "response_body": response_body[:200],
        }

    return {
        "sent": True,
        "status_code": status_code,
        "response_body": response_body[:200],
    }


def notify_cycle_summary(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> dict[str, Any]:
    text = _build_cycle_text(status_payload, git_info, run_date)
    return _post_text(text)


def notify_cycle_failure(device_id: str, cycle_id: str, day: int, ts: datetime) -> dict[str, Any]:
    text = _build_failure_text(device_id, cycle_id, day, ts)
    return _post_text(text)
