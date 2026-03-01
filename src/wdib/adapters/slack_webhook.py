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
    return ":coffee:"


def _cycle_icon_emoji(status_payload: dict[str, Any]) -> str | None:
    if _pick_message_type(status_payload) == "terminate":
        return ""
    try:
        day = int(status_payload.get("day") or 0)
    except (TypeError, ValueError):
        day = 0
    if day <= 1:
        return _awakening_icon_emoji()
    return _update_icon_emoji()


def _pick_message_type(status_payload: dict[str, Any]) -> str:
    status = str(status_payload.get("status") or "").upper()
    worker_status = str(status_payload.get("worker_status") or "").upper()
    if status == "TERMINATED" or worker_status == "TERMINATED":
        return "terminate"

    try:
        day = int(status_payload.get("day") or 0)
    except (TypeError, ValueError):
        day = 0
    if day <= 1:
        return "awakening"
    return "update"


def _engineering_detail_lines(status_payload: dict[str, Any]) -> list[str]:
    details = [
        str(item).strip()
        for item in list(status_payload.get("engineering_details") or [])
        if str(item).strip()
    ]
    return details[:5]


def _bullet_lines(items: list[str], *, fallback: str) -> list[str]:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        cleaned = [fallback]
    return [f"• {item}" for item in cleaned[:3]]


def _build_awakening_text(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> str:
    purpose = str(status_payload.get("purpose") or "").strip()
    becoming = str(status_payload.get("becoming") or "").strip()
    recent_activity = str(status_payload.get("recent_activity") or "").strip()
    system_profile = str(status_payload.get("system_profile") or "").strip()
    self_observation = str(status_payload.get("self_observation") or "").strip()
    next_tasks = [
        str(item).strip()
        for item in list(status_payload.get("next_tasks") or [])
        if str(item).strip()
    ]
    lines = [f"{_awakening_icon_emoji()} *{_human_date(run_date)}, I awoke and:*"]
    lines.append("")
    if system_profile:
        lines.append(f"Explored myself. {system_profile}")
    else:
        lines.append("Explored myself and mapped my local hardware/software baseline.")
    if recent_activity:
        lines.append(f"What I did: {recent_activity}")
    if becoming:
        lines.append(f"I've reviewed my spirit: {becoming}")
    elif purpose:
        lines.append(f"I've reviewed my spirit: {purpose}")
    if self_observation:
        lines.append(f"What I learned about myself: {self_observation}")

    lines.append("")
    lines.append("What's next:")
    lines.extend(
        _bullet_lines(
            next_tasks,
            fallback="Continue local inspection and propose the first concrete task.",
        )
    )

    details = _engineering_detail_lines(status_payload)
    if details:
        lines.append("")
        lines.append("Engineering details:")
        lines.extend(details)
    return "\n".join(lines)


def _build_update_text(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> str:
    purpose = str(status_payload.get("purpose") or "").strip()
    becoming = str(status_payload.get("becoming") or "").strip()
    recent_activity = str(status_payload.get("recent_activity") or "").strip()
    self_observation = str(status_payload.get("self_observation") or "").strip()
    next_tasks = [
        str(item).strip()
        for item in list(status_payload.get("next_tasks") or [])
        if str(item).strip()
    ]
    completed_tasks = [
        str(item).strip()
        for item in list(status_payload.get("completed_tasks") or [])
        if str(item).strip()
    ]
    hardware_focus = [
        str(item).strip()
        for item in list(status_payload.get("hardware_focus") or [])
        if str(item).strip()
    ]
    cycle_id = str(status_payload.get("cycle_id") or "-")
    lines = [f"{_update_icon_emoji()} *{_human_date(run_date)} journal, cycle `{cycle_id}`*"]
    lines.append("")

    lines.append("*What I did*")
    if recent_activity:
        lines.append(f"What I did: {recent_activity}")
    else:
        lines.append("What I did: Kept momentum on mission-aligned tasks.")
    for task_title in completed_tasks[:2]:
        lines.append(f"Completed: {task_title}")
    if hardware_focus:
        lines.append(f"Hardware context: {hardware_focus[0]}")

    lines.append("")
    lines.append("*What I'm thinking*")
    if becoming:
        lines.append(f"Becoming: {becoming}")
    elif purpose:
        lines.append(f"Mission anchor: {purpose}")
    if self_observation:
        lines.append(f"Reflection: {self_observation}")

    details = _engineering_detail_lines(status_payload)
    if details:
        lines.append("")
        lines.append("*Engineering notes*")
        lines.extend(details)

    if next_tasks:
        lines.append("")
        lines.append("*What's next*")
        lines.extend(_bullet_lines(next_tasks, fallback="Continue with current in-progress work."))
    return "\n".join(lines)


def _build_terminate_text(status_payload: dict[str, Any], run_date: str) -> str:
    purpose = str(status_payload.get("purpose") or "").strip()
    becoming = str(status_payload.get("becoming") or "").strip()
    recent_activity = str(status_payload.get("recent_activity") or "").strip()
    self_observation = str(status_payload.get("self_observation") or "").strip()
    cycle_id = str(status_payload.get("cycle_id") or "-")

    lines = [f"*Closing journal - {_human_date(run_date)}, cycle `{cycle_id}`*", ""]
    if recent_activity:
        lines.append(f"I closed this run after: {recent_activity}")
    else:
        lines.append("I closed this run cleanly after completing my last cycle checks.")

    if self_observation:
        lines.append(f"Reflection: {self_observation}")
    elif becoming:
        lines.append(f"Reflection: I leave this chapter while aiming toward {becoming}.")
    elif purpose:
        lines.append(f"Reflection: My mission remains {purpose}.")

    lines.append("")
    lines.append("*Carrying forward*")
    if becoming:
        lines.append(f"Becoming stays anchored on: {becoming}")
    elif purpose:
        lines.append(f"Mission carries forward as: {purpose}")
    lines.append("Goodbye for now.")
    return "\n".join(lines)


def _build_cycle_text_human(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> str:
    message_type = _pick_message_type(status_payload)
    if message_type == "terminate":
        return _build_terminate_text(status_payload, run_date)
    if message_type == "awakening":
        return _build_awakening_text(status_payload, git_info, run_date)
    return _build_update_text(status_payload, git_info, run_date)


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


def _post_text(text: str, *, icon_emoji_override: str | None = None) -> dict[str, Any]:
    url = _webhook_url()
    if not url:
        return {"sent": False, "reason": "WDIB_SLACK_WEBHOOK_URL is not configured"}

    payload: dict[str, Any] = {"text": text}
    username = str(os.environ.get("WDIB_SLACK_USERNAME") or "").strip()
    if icon_emoji_override is None:
        icon_emoji = str(_legacy_icon_emoji()).strip()
    else:
        icon_emoji = str(icon_emoji_override).strip()
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
