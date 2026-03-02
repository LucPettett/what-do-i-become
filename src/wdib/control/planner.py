"""Build WDIB work orders from current control-plane state."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from ..policy.safety import work_order_constraints

_MAX_CONSECUTIVE_SELECTIONS = 2


def _today() -> str:
    return date.today().isoformat()


def _parse_defer_date(raw: str) -> date | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _selection_streak(task: dict[str, Any]) -> int:
    try:
        value = int(task.get("selection_streak") or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, value)


def _is_task_deferred(task: dict[str, Any], *, today: date) -> bool:
    defer_until = _parse_defer_date(str(task.get("defer_until") or ""))
    if not defer_until:
        return False
    return defer_until > today


def _refresh_deferred_tasks(tasks: list[dict[str, Any]], events: list[dict[str, Any]]) -> None:
    today = date.today()
    for task in tasks:
        task_id = str(task.get("id") or "")
        defer_until_raw = str(task.get("defer_until") or "").strip()
        if not defer_until_raw:
            continue
        defer_until = _parse_defer_date(defer_until_raw)
        if not defer_until:
            task["defer_until"] = None
            task["defer_reason"] = ""
            events.append(
                {
                    "type": "TASK_DEFER_INVALID",
                    "task_id": task_id,
                    "value": defer_until_raw,
                    "reason": "Invalid defer_until date format; cleared by planner.",
                }
            )
            continue
        if defer_until <= today:
            task["defer_until"] = None
            task["defer_reason"] = ""
            events.append(
                {
                    "type": "TASK_DEFER_RELEASED",
                    "task_id": task_id,
                    "defer_until": defer_until_raw,
                    "reason": "Deferred date reached; task is eligible for planning again.",
                }
            )


def _pick_task(tasks: list[dict[str, Any]]) -> tuple[int | None, bool, dict[str, Any] | None]:
    today = date.today()
    in_progress_indexes = [
        idx
        for idx, task in enumerate(tasks)
        if str(task.get("status") or "") == "IN_PROGRESS" and not _is_task_deferred(task, today=today)
    ]
    todo_indexes = [
        idx
        for idx, task in enumerate(tasks)
        if str(task.get("status") or "") == "TODO" and not _is_task_deferred(task, today=today)
    ]

    if in_progress_indexes:
        ordered_in_progress = sorted(
            in_progress_indexes,
            key=lambda idx: (_selection_streak(tasks[idx]), idx),
        )
        candidate_idx = ordered_in_progress[0]
        candidate_streak = _selection_streak(tasks[candidate_idx])
        if candidate_streak < _MAX_CONSECUTIVE_SELECTIONS or not todo_indexes:
            return candidate_idx, False, None
        promoted_idx = todo_indexes[0]
        promoted_task = tasks[promoted_idx]
        rotated_task = tasks[candidate_idx]
        return (
            promoted_idx,
            True,
            {
                "type": "TASK_PLANNER_ROTATED",
                "from_task_id": str(rotated_task.get("id") or ""),
                "to_task_id": str(promoted_task.get("id") or ""),
                "reason": (
                    "Current IN_PROGRESS task reached planner selection streak limit; "
                    "rotated to another TODO task to avoid stagnation."
                ),
            },
        )

    if todo_indexes:
        return todo_indexes[0], True, None

    return None, False, None


def _record_task_selection(tasks: list[dict[str, Any]], selected_index: int | None) -> None:
    for idx, task in enumerate(tasks):
        if idx == selected_index:
            task["selection_streak"] = _selection_streak(task) + 1
            continue
        if task.get("selection_streak"):
            task["selection_streak"] = 0


def plan_work_order(
    state: dict[str, Any],
    *,
    device_id: str,
    cycle_id: str,
    mission_text: str,
    result_path: Path,
    allowed_paths: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    tasks = state.get("tasks", [])
    _refresh_deferred_tasks(tasks, events)

    task_index, promoted, rotation_event = _pick_task(tasks)
    selected_task = tasks[task_index] if task_index is not None else None

    if promoted and selected_task is not None:
        selected_task["status"] = "IN_PROGRESS"
        selected_task["updated_on"] = _today()
        events.append(
            {
                "type": "TASK_STATUS_CHANGED",
                "task_id": selected_task.get("id", ""),
                "from": "TODO",
                "to": "IN_PROGRESS",
                "reason": "Selected by planner for current cycle.",
            }
            )

    if rotation_event:
        events.append(rotation_event)

    _record_task_selection(tasks, task_index)

    open_requests = [
        req
        for req in state.get("hardware_requests", [])
        if str(req.get("status") or "") in {"OPEN", "DETECTED"}
    ]

    mission_known = bool(str(mission_text or "").strip())

    if selected_task is not None:
        objective = f"Advance task {selected_task.get('id')}: {selected_task.get('title')}"
    elif open_requests:
        objective = (
            "Hardware requests are pending. Continue software-first progress in parallel: "
            "build interfaces, simulators/mocks, telemetry, and verification harnesses so integration is ready. "
            "Do not assume installation is complete unless WDIB marks request VERIFIED."
        )
    elif not mission_known:
        objective = (
            "Mission is currently unknown. Continue structured self-discovery across cycles: "
            "build reusable sensing/observation software, collect high-signal evidence, and document constraints. "
            "Do not lock in a new becoming quickly; earn it through repeated observations and validated capability gains."
        )
    else:
        objective = (
            "Translate mission and current state into a concrete capability roadmap and execute the highest-leverage next step. "
            "Prefer software-first prototypes, data acquisition/integration, and observability before requesting new hardware. "
            "If future hardware may be required, define requirements and verification criteria while keeping software delivery moving."
        )

    mission_excerpt = mission_text.strip()
    if len(mission_excerpt) > 2500:
        mission_excerpt = mission_excerpt[:2500].rstrip() + "\n[TRUNCATED]"

    work_order = {
        "schema_version": "1.0",
        "cycle_id": cycle_id,
        "created_on": datetime.now().isoformat(timespec="seconds"),
        "device_id": device_id,
        "objective": objective,
        "constraints": work_order_constraints(),
        "allowed_paths": allowed_paths,
        "context": {
            "becoming": str(state.get("purpose", {}).get("becoming") or ""),
            "mission_excerpt": mission_excerpt,
            "tasks": [
                {
                    "id": str(item.get("id") or ""),
                    "title": str(item.get("title") or ""),
                    "status": str(item.get("status") or ""),
                    "defer_until": str(item.get("defer_until") or ""),
                }
                for item in tasks[:20]
            ],
            "hardware_requests": [
                {
                    "id": str(item.get("id") or ""),
                    "name": str(item.get("name") or ""),
                    "status": str(item.get("status") or ""),
                }
                for item in state.get("hardware_requests", [])[:20]
            ],
            "incidents": [
                {
                    "id": str(item.get("id") or ""),
                    "title": str(item.get("title") or ""),
                    "status": str(item.get("status") or ""),
                }
                for item in state.get("incidents", [])[:20]
            ],
        },
        "result_path": str(result_path),
        "result_schema_version": "1.0",
    }

    return work_order, events
