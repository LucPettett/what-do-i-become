"""Build WDIB work orders from current control-plane state."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from ..policy.safety import work_order_constraints


def _today() -> str:
    return date.today().isoformat()


def _pick_task(tasks: list[dict[str, Any]]) -> tuple[int | None, bool]:
    for idx, task in enumerate(tasks):
        if str(task.get("status") or "") == "IN_PROGRESS":
            return idx, False
    for idx, task in enumerate(tasks):
        if str(task.get("status") or "") == "TODO":
            return idx, True
    return None, False


def plan_work_order(
    state: dict[str, Any],
    *,
    device_id: str,
    cycle_id: str,
    spirit_text: str,
    result_path: Path,
    allowed_paths: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    tasks = state.get("tasks", [])

    task_index, promoted = _pick_task(tasks)
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

    open_requests = [
        req
        for req in state.get("hardware_requests", [])
        if str(req.get("status") or "") in {"OPEN", "DETECTED"}
    ]

    if selected_task is not None:
        objective = f"Advance task {selected_task.get('id')}: {selected_task.get('title')}"
    elif open_requests:
        objective = (
            "Continue software progress while hardware requests are pending. "
            "Do not assume installation is complete unless WDIB marks request VERIFIED."
        )
    else:
        objective = (
            "Self-discover system capabilities and propose the next concrete tasks to advance purpose."
        )

    spirit_excerpt = spirit_text.strip()
    if len(spirit_excerpt) > 2500:
        spirit_excerpt = spirit_excerpt[:2500].rstrip() + "\n[TRUNCATED]"

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
            "spirit_excerpt": spirit_excerpt,
            "tasks": [
                {
                    "id": str(item.get("id") or ""),
                    "title": str(item.get("title") or ""),
                    "status": str(item.get("status") or ""),
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
