"""Public-facing publication artifacts for WDIB."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_MIXED_SECRET_RE = re.compile(r"\b(?=\w*[A-Za-z])(?=\w*\d)[A-Za-z0-9]{12,}\b")
_UNIX_PATH_RE = re.compile(r"(?:^|[\s(`\"'])/(?:[A-Za-z0-9._-]+/)+[A-Za-z0-9._-]+")
_SPACES_RE = re.compile(r"\s+")
_PAIR_EVIDENCE_RE = re.compile(r"`([^`]+)`\s*=>\s*`([^`]+)`")
_VERB_EVIDENCE_RE = re.compile(r"`([^`]+)`\s+(?:shows?|found|reported)\s+([^;]+)", re.IGNORECASE)
_TEMP_C_RE = re.compile(r"~\s*([0-9]+(?:\.[0-9]+)?)C", re.IGNORECASE)


def _ordinal(day: int) -> str:
    if 10 <= (day % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _sanitize(text: str, *, max_len: int = 180) -> str:
    if not text:
        return ""

    value = text
    value = _URL_RE.sub("[redacted-url]", value)
    value = _EMAIL_RE.sub("[redacted-email]", value)
    value = _IPV4_RE.sub("[redacted-ip]", value)
    value = _MAC_RE.sub("[redacted-mac]", value)
    value = _UUID_RE.sub("[redacted-id]", value)
    value = _MIXED_SECRET_RE.sub("[redacted-token]", value)
    value = _UNIX_PATH_RE.sub(" [redacted-path]", value)
    value = _SPACES_RE.sub(" ", value).strip()
    if len(value) > max_len:
        return value[: max_len - 1].rstrip() + "..."
    return value


def _count_status(items: list[dict[str, Any]], expected: str) -> int:
    target = expected.upper()
    return sum(1 for item in items if str(item.get("status") or "").upper() == target)


def _next_task_titles(tasks: list[dict[str, Any]]) -> list[str]:
    picked: list[str] = []
    for desired in ("IN_PROGRESS", "TODO"):
        for task in tasks:
            status = str(task.get("status") or "").upper()
            if status != desired:
                continue
            title = _sanitize(str(task.get("title") or ""), max_len=100)
            if title and title not in picked:
                picked.append(title)
            if len(picked) >= 3:
                return picked
    return picked


def _completed_task_titles(tasks: list[dict[str, Any]], *, run_date: str) -> list[str]:
    done_today: list[str] = []
    done_any: list[str] = []
    for task in tasks:
        if str(task.get("status") or "").upper() != "DONE":
            continue
        title = _sanitize(str(task.get("title") or ""), max_len=100)
        if not title:
            continue
        updated_on = str(task.get("updated_on") or "")
        if updated_on == run_date and title not in done_today:
            done_today.append(title)
        if title not in done_any:
            done_any.append(title)
    if done_today:
        return done_today[:3]
    return done_any[:3]


def _hardware_focus(hardware_requests: list[dict[str, Any]]) -> list[str]:
    focus: list[str] = []
    for request in hardware_requests:
        status = str(request.get("status") or "").upper()
        if status not in {"OPEN", "DETECTED"}:
            continue
        name = _sanitize(str(request.get("name") or "Hardware item"), max_len=80)
        reason = _sanitize(str(request.get("reason") or ""), max_len=120)
        if reason:
            line = f"{name}: {reason}"
        else:
            line = name
        if status == "DETECTED":
            line = f"{line} (detected, awaiting verification)"
        focus.append(line)
        if len(focus) >= 3:
            break
    return focus


def _extract_summary_evidence_lines(summary_hint: str) -> list[str]:
    raw = str(summary_hint or "").strip()
    if not raw:
        return []

    picked: list[str] = []
    for command, result in _PAIR_EVIDENCE_RE.findall(raw):
        cmd = _sanitize(command, max_len=80)
        out = _sanitize(result, max_len=120)
        if not cmd or not out:
            continue
        line = f"`{cmd}` -> {out}"
        if line not in picked:
            picked.append(line)
        if len(picked) >= 5:
            return picked

    for command, detail in _VERB_EVIDENCE_RE.findall(raw):
        cmd = _sanitize(command, max_len=80)
        out = _sanitize(detail, max_len=120)
        if not cmd or not out:
            continue
        line = f"`{cmd}` -> {out}"
        if line not in picked:
            picked.append(line)
        if len(picked) >= 5:
            return picked
    return picked


def _system_profile_from_summary(summary_hint: str) -> str:
    raw = str(summary_hint or "").strip()
    lowered = raw.lower()
    if not lowered:
        return ""

    parts: list[str] = []
    if "raspberry pi" in lowered:
        parts.append("I am running on Raspberry Pi hardware")
    if "wlan0" in lowered and "up" in lowered:
        parts.append("wlan0 is online")
    if "0% packet loss" in lowered or "http/2 200" in lowered:
        parts.append("outbound connectivity checks passed")
    if "/dev/i2c" in lowered or "i2c-" in lowered:
        parts.append("I2C buses are available")
    if "/dev/video" in lowered or "v4l" in lowered:
        parts.append("video device nodes are present")
    if "arecord -l" in lowered and "no capture device" in lowered:
        parts.append("no microphone capture device was detected")

    temp_match = _TEMP_C_RE.search(raw)
    if temp_match:
        parts.append(f"CPU temperature is around {temp_match.group(1)}C")

    if not parts:
        return ""
    return _sanitize("; ".join(parts) + ".", max_len=240)


def _engineering_details(
    summary_hint: str,
    *,
    completed_tasks: list[str],
    artifacts: list[dict[str, Any]],
) -> list[str]:
    details: list[str] = []
    for title in completed_tasks[:2]:
        cleaned = _sanitize(str(title), max_len=110)
        if cleaned:
            details.append(f"Completed task: {cleaned}")

    for line in _extract_summary_evidence_lines(summary_hint):
        if line not in details:
            details.append(line)
        if len(details) >= 6:
            return details

    for item in artifacts[-3:]:
        description = _sanitize(str(item.get("description") or ""), max_len=120)
        if not description:
            continue
        artifact_line = f"Artifact: {description}"
        if artifact_line not in details:
            details.append(artifact_line)
        if len(details) >= 6:
            return details

    return details


def _safe_reflection(summary_hint: str) -> str:
    cleaned = _sanitize(summary_hint, max_len=160)
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    blocked_markers = (
        "`",
        "state.json",
        "events.ndjson",
        "worker_result",
        "incident-",
        "cycle-",
        "codex",
        "python3",
        "pytest",
        "trace",
    )
    if any(marker in lowered for marker in blocked_markers):
        return ""
    return cleaned


def _extract_spirit_purpose(spirit_text: str) -> str:
    raw = str(spirit_text or "")
    if not raw.strip():
        return ""

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return ""

    for idx, line in enumerate(lines):
        normalized = line.lstrip("#").strip().lower()
        if normalized != "mission":
            continue
        for candidate in lines[idx + 1 :]:
            if candidate.startswith("#"):
                break
            cleaned = candidate.lstrip("-* ").strip()
            if cleaned:
                return _sanitize(cleaned, max_len=180)
        break

    for line in lines:
        if line.startswith("#") or line.startswith("```"):
            continue
        cleaned = line.lstrip("-* ").strip()
        if cleaned:
            return _sanitize(cleaned, max_len=180)
    return ""


def _recent_activity(summary_hint: str, objective_hint: str) -> str:
    summary_text = str(summary_hint or "").strip()
    if summary_text:
        trimmed = summary_text
        for marker in (
            "Verification evidence:",
            "Commands run:",
            "State/context probes:",
            "Result contract verification:",
        ):
            idx = trimmed.find(marker)
            if idx != -1:
                trimmed = trimmed[:idx].strip()
        reflected = _safe_reflection(trimmed)
        if reflected:
            lowered = reflected.lower()
            if "proposed next tasks" in lowered:
                return "Inspected local context and drafted the next tasks."
            if "capability discovery" in lowered:
                return "Completed capability discovery and mapped the next steps."
            return reflected

    objective = str(objective_hint or "").strip()
    if objective:
        if objective.startswith("Advance task "):
            _, _, suffix = objective.partition(":")
            candidate = suffix.strip() or objective
            return f"Worked on: {_sanitize(candidate, max_len=150)}"
        lowered = objective.lower()
        if "hardware requests are pending" in lowered:
            return "Kept software work moving while waiting for hardware verification."
        if "inspect local physical/environment context" in lowered:
            return "Inspected local environment and planned practical next steps."
        return _sanitize(objective, max_len=160)

    return "Made steady progress on mission-aligned work."


def _self_observation(
    tasks: list[dict[str, Any]],
    hardware_requests: list[dict[str, Any]],
    incidents: list[dict[str, Any]],
) -> str:
    waiting_hardware = sum(
        1 for item in hardware_requests if str(item.get("status") or "").upper() in {"OPEN", "DETECTED"}
    )
    incidents_open = _count_status(incidents, "OPEN")
    in_progress = _count_status(tasks, "IN_PROGRESS")
    todo = _count_status(tasks, "TODO")

    if waiting_hardware > 0:
        return (
            "I can reason and plan in software, but I still need physical hardware "
            "verification before I can complete this part of my mission."
        )
    if incidents_open > 0:
        return "I found reliability issues that I need to resolve before I can trust this path."
    if in_progress > 0 or todo > 0:
        return "I have enough clarity and momentum to keep improving tomorrow."
    return "I am still mapping my environment and defining the next meaningful step."


def build_public_status(
    *,
    device_id: str,
    cycle_id: str,
    day: int,
    state: dict[str, Any],
    worker_status: str,
    spirit_text: str = "",
    summary_hint: str = "",
    objective_hint: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    at = now or datetime.now()
    run_date = at.date().isoformat()
    tasks = list(state.get("tasks") or [])
    hardware_requests = list(state.get("hardware_requests") or [])
    incidents = list(state.get("incidents") or [])
    state_status = str(state.get("status") or "UNKNOWN")
    terminated = state_status.upper() == "TERMINATED"
    completed_tasks = _completed_task_titles(tasks, run_date=run_date)
    next_tasks = [] if terminated else _next_task_titles(tasks)
    hardware_focus = [] if terminated else _hardware_focus(hardware_requests)
    system_profile = "" if terminated else _system_profile_from_summary(summary_hint)
    engineering_details = _engineering_details(
        summary_hint,
        completed_tasks=completed_tasks,
        artifacts=list(state.get("artifacts") or []),
    )
    self_observation = (
        "I received a human termination command and gracefully closed this chapter."
        if terminated
        else _self_observation(tasks, hardware_requests, incidents)
    )

    return {
        "schema_version": "1.0",
        "device_id_short": device_id[:8],
        "cycle_id": cycle_id,
        "updated_at": at.isoformat(timespec="seconds"),
        "date": at.date().isoformat(),
        "first_awoke_on": str(state.get("awoke_on") or at.date().isoformat()),
        "day": int(day),
        "status": state_status,
        "worker_status": str(worker_status or "UNKNOWN"),
        "purpose": _extract_spirit_purpose(spirit_text) or "Unset (add a mission in SPIRIT.md).",
        "becoming": _sanitize(str((state.get("purpose") or {}).get("becoming") or "")),
        "recent_activity": _recent_activity(summary_hint, objective_hint),
        "system_profile": system_profile,
        "completed_tasks": completed_tasks,
        "next_tasks": next_tasks,
        "hardware_focus": hardware_focus,
        "engineering_details": engineering_details,
        "self_observation": self_observation,
        "counts": {
            "tasks": {
                "todo": _count_status(tasks, "TODO"),
                "in_progress": _count_status(tasks, "IN_PROGRESS"),
                "done": _count_status(tasks, "DONE"),
                "blocked": _count_status(tasks, "BLOCKED"),
            },
            "hardware_requests": {
                "open": _count_status(hardware_requests, "OPEN"),
                "detected": _count_status(hardware_requests, "DETECTED"),
                "verified": _count_status(hardware_requests, "VERIFIED"),
                "failed": _count_status(hardware_requests, "FAILED"),
            },
            "incidents_open": _count_status(incidents, "OPEN"),
        },
        "public_notice": "Sanitized publication only. Detailed logs remain on-device.",
    }


def build_public_daily_summary(
    *,
    status_payload: dict[str, Any],
    objective: str,
    summary_hint: str,
    now: datetime | None = None,
) -> str:
    at = now or datetime.now()
    human_date = f"{at.strftime('%A')} {_ordinal(at.day)} {at.strftime('%B %Y')}"
    becoming = str(status_payload.get("becoming") or "").strip()
    status = str(status_payload.get("status") or "UNKNOWN")
    worker_status = str(status_payload.get("worker_status") or "UNKNOWN")
    counts = status_payload.get("counts") or {}
    task_counts = counts.get("tasks") or {}
    hardware_counts = counts.get("hardware_requests") or {}
    incidents_open = int(counts.get("incidents_open") or 0)

    cleaned_objective = _sanitize(objective, max_len=200)
    cleaned_hint = _safe_reflection(summary_hint)

    lines = [
        f"# Day {int(status_payload.get('day') or 0):03d} - {human_date}",
        "",
        "I awoke and:",
        "- Reflected on what I should become.",
    ]
    if becoming:
        lines.append(f"- Held this direction: {becoming}")
    if cleaned_objective:
        lines.append(f"- Focused on this step: {cleaned_objective}")
    lines.extend(
        [
            "- Inspected myself and my local environment.",
            f"- Finished this cycle with status `{status}`.",
            "",
            "## Snapshot",
            f"- Device: `{status_payload.get('device_id_short', '-')}`",
            f"- Cycle: `{status_payload.get('cycle_id', '-')}`",
            f"- Worker: `{worker_status}`",
            (
                "- Tasks: "
                f"{int(task_counts.get('todo') or 0)} TODO, "
                f"{int(task_counts.get('in_progress') or 0)} IN_PROGRESS, "
                f"{int(task_counts.get('done') or 0)} DONE, "
                f"{int(task_counts.get('blocked') or 0)} BLOCKED"
            ),
            (
                "- Hardware requests: "
                f"{int(hardware_counts.get('open') or 0)} OPEN, "
                f"{int(hardware_counts.get('detected') or 0)} DETECTED, "
                f"{int(hardware_counts.get('verified') or 0)} VERIFIED, "
                f"{int(hardware_counts.get('failed') or 0)} FAILED"
            ),
            f"- Open incidents: {incidents_open}",
            "",
            "## Note",
            "- This is a sanitized public summary. Raw logs and detailed traces stay on-device.",
        ]
    )

    if cleaned_hint:
        lines.extend(["", "## Reflection", f"- {cleaned_hint}"])

    return "\n".join(lines) + "\n"
