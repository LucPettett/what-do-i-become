"""Apply worker results to canonical WDIB state."""

from __future__ import annotations

from datetime import date
from typing import Any


def _today() -> str:
    return date.today().isoformat()


def _append_note(existing: str, note: str) -> str:
    prefix = existing.strip()
    line = f"[{_today()}] {note}"
    if not prefix:
        return line
    return f"{prefix}\n{line}"


def _parse_defer_date(raw: str) -> str | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _next_id(existing: list[str], prefix: str) -> str:
    counter = 1
    existing_set = set(existing)
    while True:
        candidate = f"{prefix}-{date.today().strftime('%Y%m%d')}-{counter:03d}"
        if candidate not in existing_set:
            return candidate
        counter += 1


def _upsert_task_updates(state: dict[str, Any], updates: list[dict[str, Any]], events: list[dict[str, Any]]) -> None:
    tasks = state.get("tasks", [])
    by_id = {str(task.get("id") or ""): task for task in tasks}

    for update in updates:
        task_id = str(update.get("task_id") or "")
        task = by_id.get(task_id)
        if not task:
            continue

        previous = str(task.get("status") or "TODO")
        target = str(update.get("status") or previous)
        metadata_changed = False
        if previous != target:
            task["status"] = target
            task["updated_on"] = _today()
            if target == "DONE":
                task["completed_on"] = _today()
            elif task.get("completed_on"):
                task["completed_on"] = None
            if target == "DONE":
                task["defer_until"] = None
                task["defer_reason"] = ""
                task["selection_streak"] = 0
            events.append(
                {
                    "type": "TASK_STATUS_CHANGED",
                    "task_id": task_id,
                    "from": previous,
                    "to": target,
                    "reason": "worker_result.task_updates",
                }
            )

        defer_until_present = "defer_until" in update
        defer_reason_present = "defer_reason" in update
        if defer_until_present:
            previous_defer_until = str(task.get("defer_until") or "").strip()
            raw_defer_until = str(update.get("defer_until") or "").strip()
            if not raw_defer_until:
                if previous_defer_until:
                    task["defer_until"] = None
                    task["defer_reason"] = ""
                    metadata_changed = True
                    events.append(
                        {
                            "type": "TASK_DEFER_CLEARED",
                            "task_id": task_id,
                            "reason": "worker_result.task_updates cleared defer_until",
                        }
                    )
            else:
                parsed_defer_until = _parse_defer_date(raw_defer_until)
                if not parsed_defer_until:
                    task["defer_until"] = None
                    task["defer_reason"] = ""
                    metadata_changed = True
                    events.append(
                        {
                            "type": "TASK_DEFER_INVALID",
                            "task_id": task_id,
                            "value": raw_defer_until,
                            "reason": "worker_result.task_updates.defer_until is not a valid YYYY-MM-DD date",
                        }
                    )
                elif previous_defer_until != parsed_defer_until:
                    task["defer_until"] = parsed_defer_until
                    metadata_changed = True
                    events.append(
                        {
                            "type": "TASK_DEFER_SET",
                            "task_id": task_id,
                            "defer_until": parsed_defer_until,
                        }
                    )

        if defer_reason_present:
            raw_defer_reason = str(update.get("defer_reason") or "").strip()
            current_defer_until = str(task.get("defer_until") or "").strip()
            normalized_defer_reason = raw_defer_reason if current_defer_until else ""
            if str(task.get("defer_reason") or "") != normalized_defer_reason:
                task["defer_reason"] = normalized_defer_reason
                metadata_changed = True

        if metadata_changed and previous == target:
            task["updated_on"] = _today()

        note = str(update.get("note") or "").strip()
        if note:
            task["notes"] = _append_note(str(task.get("notes") or ""), note)


def _append_proposed_tasks(state: dict[str, Any], proposed_tasks: list[dict[str, Any]], events: list[dict[str, Any]]) -> None:
    tasks = state.get("tasks", [])
    open_titles = {
        str(task.get("title") or "").strip().lower()
        for task in tasks
        if str(task.get("status") or "") != "DONE"
    }

    existing_ids = [str(task.get("id") or "") for task in tasks]

    for item in proposed_tasks:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        title_key = title.lower()
        if title_key in open_titles:
            continue

        task_id = _next_id(existing_ids, "task")
        existing_ids.append(task_id)
        open_titles.add(title_key)

        status = str(item.get("status") or "TODO")
        if status not in {"TODO", "IN_PROGRESS", "DONE", "BLOCKED"}:
            status = "TODO"

        task = {
            "id": task_id,
            "title": title,
            "description": str(item.get("description") or ""),
            "status": status,
            "blocked_by": str(item.get("blocked_by") or ""),
            "created_on": _today(),
            "updated_on": _today(),
            "completed_on": _today() if status == "DONE" else None,
            "defer_until": None,
            "defer_reason": "",
            "selection_streak": 0,
            "notes": str(item.get("notes") or ""),
        }
        tasks.append(task)
        events.append(
            {
                "type": "TASK_CREATED",
                "task_id": task_id,
                "title": title,
            }
        )


def _append_proposed_hardware_requests(
    state: dict[str, Any],
    proposed: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> None:
    requests = state.get("hardware_requests", [])
    open_name_keys = {
        str(req.get("name") or "").strip().lower()
        for req in requests
        if str(req.get("status") or "") in {"OPEN", "DETECTED"}
    }
    existing_ids = [str(req.get("id") or "") for req in requests]

    for item in proposed:
        name = str(item.get("name") or "").strip()
        reason = str(item.get("reason") or "").strip()
        detection = item.get("detection") or {}
        detection_kind = str(detection.get("kind") or "").strip()
        detection_value = str(detection.get("value") or "").strip()
        if not name or not reason or not detection_kind or not detection_value:
            continue

        key = name.lower()
        if key in open_name_keys:
            continue

        request_id = _next_id(existing_ids, "hardware")
        existing_ids.append(request_id)
        open_name_keys.add(key)

        request = {
            "id": request_id,
            "name": name,
            "reason": reason,
            "status": "OPEN",
            "detection": {
                "kind": detection_kind,
                "value": detection_value,
            },
            "verify_command": str(item.get("verify_command") or ""),
            "requested_on": _today(),
            "last_checked_on": None,
            "detected_on": None,
            "verified_on": None,
            "verify_failures": 0,
            "notes": str(item.get("notes") or ""),
        }
        requests.append(request)
        events.append(
            {
                "type": "HARDWARE_REQUEST_CREATED",
                "request_id": request_id,
                "name": name,
            }
        )


def _append_incidents(state: dict[str, Any], proposed: list[dict[str, Any]], events: list[dict[str, Any]]) -> None:
    incidents = state.get("incidents", [])
    existing_ids = [str(item.get("id") or "") for item in incidents]

    for item in proposed:
        title = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        severity = str(item.get("severity") or "MEDIUM").strip().upper()
        status = str(item.get("status") or "OPEN").strip().upper()

        if not title or not summary:
            continue
        if severity not in {"LOW", "MEDIUM", "HIGH"}:
            severity = "MEDIUM"
        if status not in {"OPEN", "RESOLVED"}:
            status = "OPEN"

        incident_id = _next_id(existing_ids, "incident")
        existing_ids.append(incident_id)
        incidents.append(
            {
                "id": incident_id,
                "title": title,
                "status": status,
                "severity": severity,
                "summary": summary,
                "created_on": _today(),
                "updated_on": _today(),
            }
        )
        events.append(
            {
                "type": "INCIDENT_CREATED",
                "incident_id": incident_id,
                "title": title,
                "severity": severity,
            }
        )


def _append_artifacts(state: dict[str, Any], artifacts: list[dict[str, Any]]) -> None:
    sink = state.setdefault("artifacts", [])
    for item in artifacts:
        path = str(item.get("path") or "").strip()
        description = str(item.get("description") or "").strip()
        if not path or not description:
            continue
        sink.append(
            {
                "path": path,
                "description": description,
                "created_on": _today(),
            }
        )


def _derive_status(state: dict[str, Any], worker_status: str) -> str:
    if worker_status == "FAILED":
        return "ERROR"

    has_unverified_hardware = any(
        str(req.get("status") or "") in {"OPEN", "DETECTED"}
        for req in state.get("hardware_requests", [])
    )
    if has_unverified_hardware:
        return "BLOCKED_HARDWARE"
    return "ACTIVE"


def apply_worker_result(state: dict[str, Any], worker_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Mutate state according to worker_result contract and return event list."""
    events: list[dict[str, Any]] = []

    _append_proposed_tasks(state, worker_result.get("proposed_tasks") or [], events)
    _upsert_task_updates(state, worker_result.get("task_updates") or [], events)
    _append_proposed_hardware_requests(
        state,
        worker_result.get("proposed_hardware_requests") or [],
        events,
    )
    _append_incidents(state, worker_result.get("incidents") or [], events)
    _append_artifacts(state, worker_result.get("artifacts") or [])

    becoming = str(worker_result.get("becoming") or "").strip()
    if becoming:
        old = str(state.get("purpose", {}).get("becoming") or "")
        if old != becoming:
            state.setdefault("purpose", {})["becoming"] = becoming
            events.append(
                {
                    "type": "BECOMING_UPDATED",
                    "from": old,
                    "to": becoming,
                }
            )

    summary = str(worker_result.get("summary") or "").strip()
    state["last_summary"] = summary

    worker_status = str(worker_result.get("status") or "COMPLETED")
    if worker_status == "FAILED":
        _append_incidents(
            state,
            [
                {
                    "title": "Worker execution failed",
                    "summary": summary or "Worker returned FAILED status.",
                    "severity": "HIGH",
                    "status": "OPEN",
                }
            ],
            events,
        )

    state["status"] = _derive_status(state, worker_status)
    return events
