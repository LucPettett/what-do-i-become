"""Slack Incoming Webhook adapter for WDIB notifications."""

from __future__ import annotations

import json
import os
import re
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


def _day_number(status_payload: dict[str, Any]) -> int:
    try:
        day = int(status_payload.get("day") or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, day)


def _cycle_heading(status_payload: dict[str, Any], run_date: str) -> str:
    message_type = _pick_message_type(status_payload)
    if message_type == "terminate":
        return ""

    day = _day_number(status_payload)
    day_label = f"DAY {day}" if day > 0 else "DAY ?"
    if message_type == "awakening":
        day_label = f"{day_label}: Awakening"

    icon = _awakening_icon_emoji() if message_type == "awakening" else _update_icon_emoji()
    return f"{icon} *{_human_date(run_date)}: {day_label}*"


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
    lines = [_cycle_heading(status_payload, run_date)]
    lines.append("")
    if system_profile:
        lines.append(f"Explored myself. {system_profile}")
    else:
        lines.append("Explored myself and mapped my local hardware/software baseline.")
    if recent_activity:
        lines.append(f"What I did: {recent_activity}")
    if becoming:
        lines.append(f"I've reviewed my mission: {becoming}")
    elif purpose:
        lines.append(f"I've reviewed my mission: {purpose}")
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
    lines = [_cycle_heading(status_payload, run_date)]
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
    completed_tasks = [
        str(item).strip()
        for item in list(status_payload.get("completed_tasks") or [])
        if str(item).strip()
    ]
    engineering_details = _engineering_detail_lines(status_payload)

    lines = [f"*Closing journal - ✌️ {_human_date(run_date)}, I've been told to terminate*", ""]
    lines.append("I've just received a human termination instruction and gracefully ended this run.")
    if recent_activity:
        lines.append(f"Cycle context: {recent_activity}")

    lines.append("")
    lines.append("Final thoughts:")
    if completed_tasks:
        lines.append(f"We completed: {'; '.join(completed_tasks[:3])}.")
    if engineering_details:
        lines.append(f"Engineering highlights: {'; '.join(engineering_details[:2])}.")
    if self_observation:
        lines.append(f"I learned: {self_observation}")
    elif becoming:
        lines.append(f"I learned to stay anchored on: {becoming}")
    elif purpose:
        lines.append(f"I learned to stay anchored on: {purpose}")
    lines.append("I'm terminating now. Goodbye.")
    return "\n".join(lines)


def _build_cycle_text_human(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> str:
    message_type = _pick_message_type(status_payload)
    if message_type == "terminate":
        return _build_terminate_text(status_payload, run_date)
    if message_type == "awakening":
        return _build_awakening_text(status_payload, git_info, run_date)
    return _build_update_text(status_payload, git_info, run_date)


def _slack_llm_model() -> str:
    configured = str(os.environ.get("WDIB_LLM_MODEL") or "").strip()
    if configured:
        return configured
    return "gpt-5.2"


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    value = str(raw_text or "").strip()
    if not value:
        return None
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
        return None
    except json.JSONDecodeError:
        start = value.find("{")
        end = value.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(value[start : end + 1])
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
        return None


_DOUBLE_ASTERISK_BOLD_RE = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
_DOUBLE_UNDERSCORE_BOLD_RE = re.compile(r"__(?=\S)(.+?)(?<=\S)__")


def _normalize_for_slack_mrkdwn(text: str) -> str:
    """Convert common Markdown variants into Slack mrkdwn equivalents."""
    value = str(text or "").strip()
    if not value:
        return ""
    # Slack bold is *text*, not **text** or __text__.
    value = _DOUBLE_ASTERISK_BOLD_RE.sub(r"*\1*", value)
    value = _DOUBLE_UNDERSCORE_BOLD_RE.sub(r"*\1*", value)
    return value


def _llm_prompt_context(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> dict[str, Any]:
    counts = status_payload.get("counts") or {}
    device_id_short = str(status_payload.get("device_id_short") or "-")
    system_profile = str(status_payload.get("system_profile") or "").strip()
    return {
        "message_type": _pick_message_type(status_payload),
        "device_id_short": device_id_short,
        "device_summary": system_profile or f"Device ID {device_id_short}",
        "run_date": _human_date(run_date),
        "cycle_id": str(status_payload.get("cycle_id") or "-"),
        "day": int(status_payload.get("day") or 0),
        "status": str(status_payload.get("status") or "UNKNOWN"),
        "worker_status": str(status_payload.get("worker_status") or "UNKNOWN"),
        "purpose": str(status_payload.get("purpose") or "").strip(),
        "becoming": str(status_payload.get("becoming") or "").strip(),
        "recent_activity": str(status_payload.get("recent_activity") or "").strip(),
        "system_profile": system_profile,
        "self_observation": str(status_payload.get("self_observation") or "").strip(),
        "completed_tasks": [str(item).strip() for item in list(status_payload.get("completed_tasks") or [])][:3],
        "next_tasks": [str(item).strip() for item in list(status_payload.get("next_tasks") or [])][:3],
        "hardware_focus": [str(item).strip() for item in list(status_payload.get("hardware_focus") or [])][:3],
        "engineering_details": _engineering_detail_lines(status_payload),
        "counts": {
            "tasks": dict(counts.get("tasks") or {}),
            "hardware_requests": dict(counts.get("hardware_requests") or {}),
            "incidents_open": int(counts.get("incidents_open") or 0),
        },
        "git_pushed": bool(git_info.get("pushed")),
    }


def _build_cycle_text_llm(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> str | None:
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI
    except Exception:  # noqa: BLE001
        return None

    system_prompt = (
        "You are an expert at communicating your tasks for the day.\n"
        "You will be given facts for one autonomous engineering cycle and must produce a world-class Slack update.\n"
        "You are writing an engineering journal focused on the software and hardware you build, and will build.\n"
        "Core task:\n"
        "- Provide an update focused on what you just completed.\n"
        "- Explain your thinking in relation to your core purpose.\n"
        "- Describe your recent work with concrete technical details; include command/tool evidence and code/artifact details when present.\n"
        "- Include your state of mind with emotional intelligence grounded in your mission and ambitions.\n"
        "- Finish with upcoming tasks.\n"
        "Style:\n"
        "- Be concise where possible: short lists, notes, and direct language.\n"
        "Rules:\n"
        "1) Use only facts from the provided JSON context.\n"
        "2) Keep first-person voice ('I'). Be concrete, technical, and specific.\n"
        "3) Keep it concise but detailed: 140-320 words.\n"
        "4) Use Slack mrkdwn syntax. For bold use *text* (never **text**).\n"
        "5) Never mention internal schema names, secrets, IPs, tokens, or local paths.\n"
        "6) If message_type is 'terminate', write a graceful closing note that reflects on your full lifecycle because this is your final message.\n"
        "Return strict JSON with one key: text."
    )
    context = _llm_prompt_context(status_payload, git_info, run_date)
    user_prompt = (
        "Compose a polished WDIB cycle update.\n"
        "Context JSON:\n"
        f"{json.dumps(context, indent=2, sort_keys=True)}"
    )
    response_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["text"],
        "properties": {
            "text": {
                "type": "string",
                "minLength": 1,
                "maxLength": 1800,
            }
        },
    }

    client = OpenAI()
    try:
        response = client.responses.create(
            model=_slack_llm_model(),
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "wdib_slack_cycle_message",
                    "schema": response_schema,
                    "strict": True,
                }
            },
        )
    except Exception:  # noqa: BLE001
        return None

    parsed = _extract_json_object(getattr(response, "output_text", ""))
    if not parsed:
        return None
    text = str(parsed.get("text") or "").strip()
    if not text:
        return None
    return text


def _build_cycle_text(status_payload: dict[str, Any], git_info: dict[str, Any], run_date: str) -> str:
    llm_text = _build_cycle_text_llm(status_payload, git_info, run_date)
    if llm_text:
        heading = _cycle_heading(status_payload, run_date)
        if heading:
            return f"{heading}\n\n{llm_text}"
        return llm_text
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

    payload: dict[str, Any] = {"text": _normalize_for_slack_mrkdwn(text)}
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
