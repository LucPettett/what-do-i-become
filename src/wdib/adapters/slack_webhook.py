"""Slack Incoming Webhook adapter for WDIB notifications."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
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


def _ordinal(day: int) -> str:
    if 10 <= (day % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _human_date(run_date: str) -> str:
    try:
        parsed = date.fromisoformat(run_date)
    except ValueError:
        return run_date
    return f"{parsed.strftime('%A')} {_ordinal(parsed.day)} {parsed.strftime('%B')}"


def _message_style() -> str:
    raw = str(os.environ.get("WDIB_SLACK_MESSAGE_STYLE") or "human").strip().lower()
    if raw == "detailed":
        return "detailed"
    return "human"


def _legacy_icon_emoji() -> str:
    return str(os.environ.get("WDIB_SLACK_ICON_EMOJI") or "").strip()


def _awakening_icon_emoji() -> str:
    specific = str(os.environ.get("WDIB_SLACK_AWAKENING_EMOJI") or "").strip()
    if specific:
        return specific
    legacy = _legacy_icon_emoji()
    if legacy:
        return legacy
    return ":sunrise:"


def _update_icon_emoji() -> str:
    specific = str(os.environ.get("WDIB_SLACK_UPDATE_EMOJI") or "").strip()
    if specific:
        return specific
    legacy = _legacy_icon_emoji()
    if legacy:
        return legacy
    return "☕️"


def _cycle_icon_emoji(status_payload: dict[str, Any]) -> str:
    try:
        day = int(status_payload.get("day") or 0)
    except (TypeError, ValueError):
        day = 0
    if day <= 1:
        return _awakening_icon_emoji()
    return _update_icon_emoji()


def _build_cycle_text_human(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> str:
    purpose = str(status_payload.get("purpose") or "").strip()
    becoming = str(status_payload.get("becoming") or "").strip()
    recent_activity = str(status_payload.get("recent_activity") or "").strip()
    next_tasks = [
        str(item).strip()
        for item in list(status_payload.get("next_tasks") or [])
        if str(item).strip()
    ]
    pushed = bool(git_info.get("pushed"))
    counts = status_payload.get("counts") or {}
    task_counts = counts.get("tasks") or {}
    hardware_counts = counts.get("hardware_requests") or {}
    incidents_open = int(counts.get("incidents_open") or 0)

    todo = int(task_counts.get("todo") or 0)
    in_progress = int(task_counts.get("in_progress") or 0)
    blocked = int(task_counts.get("blocked") or 0)
    waiting_hardware = int(hardware_counts.get("open") or 0) + int(hardware_counts.get("detected") or 0)

    lines = [f"*{_human_date(run_date)}, I awoke and:*"]
    if recent_activity:
        lines.append(f"- What I did: {recent_activity}")
    else:
        lines.append("- What I did: Kept moving forward on my mission.")

    if becoming:
        lines.append(f"- What I'm thinking: {becoming}")
    elif purpose:
        lines.append(f"- What I'm thinking: {purpose}")
    else:
        lines.append("- What I'm thinking: I need to define my direction more clearly.")

    if next_tasks:
        lines.append(f"- What's next: {next_tasks[0]}")
        for task_title in next_tasks[1:3]:
            lines.append(f"- Then: {task_title}")
    elif todo or in_progress or blocked:
        lines.append(f"- What's next: {in_progress} in progress, {todo} todo, {blocked} blocked.")
    else:
        lines.append("- What's next: Continue observation and propose the next concrete task.")

    if waiting_hardware:
        lines.append(f"- Waiting on hardware verification: {waiting_hardware} request(s).")
    if incidents_open:
        lines.append(f"- Open incidents to resolve: {incidents_open}.")

    if pushed:
        lines.append("- Shared a sanitized daily update to GitHub.")
    else:
        lines.append("- Saved a sanitized daily update locally (GitHub push is still pending).")
    lines.append("- Detailed logs remain on-device.")
    return "\n".join(lines)


def _build_cycle_text_detailed(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> str:
    short_id = str(status_payload.get("device_id_short") or "-")
    day = int(status_payload.get("day") or 0)
    status = str(status_payload.get("status") or "UNKNOWN")
    worker_status = str(status_payload.get("worker_status") or "UNKNOWN")
    cycle_id = str(status_payload.get("cycle_id") or "-")
    purpose = str(status_payload.get("purpose") or "").strip()
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
    if purpose:
        lines.append(f"- Purpose: {purpose}")
    if becoming:
        lines.append(f"- Becoming: {becoming}")
    lines.extend(
        [
            f"- Pushed to GitHub: `{git_mark}`",
            "- This update is sanitized; detailed logs remain on-device.",
        ]
    )
    return "\n".join(lines)


def _build_cycle_text(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> str:
    if _message_style() == "detailed":
        return _build_cycle_text_detailed(status_payload, git_info, run_date)
    return _build_cycle_text_human(status_payload, git_info, run_date)


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


def _post_text(text: str, *, icon_emoji_override: str = "") -> dict[str, Any]:
    url = _webhook_url()
    if not url:
        return {"sent": False, "reason": "WDIB_SLACK_WEBHOOK_URL is not configured"}

    payload: dict[str, Any] = {"text": text}
    username = str(os.environ.get("WDIB_SLACK_USERNAME") or "").strip()
    icon_emoji = str(icon_emoji_override or _legacy_icon_emoji()).strip()
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
    return _post_text(text, icon_emoji_override=_cycle_icon_emoji(status_payload))


def notify_cycle_failure(device_id: str, cycle_id: str, day: int, ts: datetime) -> dict[str, Any]:
    text = _build_failure_text(device_id, cycle_id, day, ts)
    return _post_text(text, icon_emoji_override=_update_icon_emoji())
