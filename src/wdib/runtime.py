"""WDIB cycle runtime."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .adapters.codex_cli import CodexRunFailure, execute_work_order
from .adapters.git_repo import commit_device_changes
from .control.hardware import probe_hardware_requests
from .control.planner import plan_work_order
from .control.reducer import apply_worker_result
from .control.spirit import load_spirit_text
from .env import load_dotenv, resolve_device_id
from .paths import PROJECT_ROOT, SPIRIT_FILE
from .policy.safety import codex_timeout_seconds, command_timeout_seconds
from .storage.repository import (
    append_event,
    device_paths,
    load_state,
    save_session_record,
    save_state,
    save_work_order,
    save_worker_result,
    worker_result_path,
)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _cycle_id(day: int) -> str:
    return f"cycle-{day:03d}-{datetime.now().strftime('%Y%m%dT%H%M%S')}"


def _next_incident_id(state: dict[str, Any]) -> str:
    prefix = f"incident-{datetime.now().strftime('%Y%m%d')}"
    existing = {
        str(item.get("id") or "")
        for item in state.get("incidents", [])
        if isinstance(item, dict)
    }
    counter = 1
    while True:
        candidate = f"{prefix}-{counter:03d}"
        if candidate not in existing:
            return candidate
        counter += 1


def _record_runtime_failure(state: dict[str, Any], message: str) -> None:
    state["status"] = "ERROR"
    state.setdefault("incidents", []).append(
        {
            "id": _next_incident_id(state),
            "title": "WDIB runtime failure",
            "status": "OPEN",
            "severity": "HIGH",
            "summary": message,
            "created_on": datetime.now().date().isoformat(),
            "updated_on": datetime.now().date().isoformat(),
        }
    )
    state["last_summary"] = message


def run_tick() -> dict[str, Any]:
    load_dotenv()

    device_id = resolve_device_id()
    spirit_text = load_spirit_text()
    spirit_path = str(SPIRIT_FILE)
    state = load_state(device_id, spirit_path=spirit_path)

    previous_day = int(state.get("day") or 0)
    day = previous_day + 1
    cycle_id = _cycle_id(day)

    append_event(
        device_id,
        {
            "type": "CYCLE_STARTED",
            "cycle_id": cycle_id,
            "day": day,
            "status": state.get("status"),
        },
    )

    try:
        hardware_events = probe_hardware_requests(state, timeout_seconds=command_timeout_seconds())
        for event in hardware_events:
            event["cycle_id"] = cycle_id
            append_event(device_id, event)

        result_path = worker_result_path(device_id, cycle_id)
        paths = device_paths(device_id)
        allowed_paths = [
            str(PROJECT_ROOT),
            str(paths["device_dir"]),
        ]

        work_order, planning_events = plan_work_order(
            state,
            device_id=device_id,
            cycle_id=cycle_id,
            spirit_text=spirit_text,
            result_path=result_path,
            allowed_paths=allowed_paths,
        )
        work_order_file = save_work_order(device_id, cycle_id, work_order)
        for event in planning_events:
            event["cycle_id"] = cycle_id
            append_event(device_id, event)

        save_state(device_id, state)

        worker_result, run_metadata = execute_work_order(
            work_order,
            project_root=Path(PROJECT_ROOT),
            timeout_seconds=codex_timeout_seconds(),
        )
        save_worker_result(device_id, cycle_id, worker_result)

        append_event(
            device_id,
            {
                "type": "WORKER_EXECUTED",
                "cycle_id": cycle_id,
                "returncode": run_metadata.get("returncode"),
                "mode": run_metadata.get("mode"),
            },
        )

        reducer_events = apply_worker_result(state, worker_result)
        for event in reducer_events:
            event["cycle_id"] = cycle_id
            append_event(device_id, event)

        state["day"] = day
        save_state(device_id, state)

        session_payload = {
            "date": datetime.now().date().isoformat(),
            "cycle_id": cycle_id,
            "day": day,
            "status": state.get("status"),
            "summary": state.get("last_summary", ""),
            "work_order_path": str(work_order_file),
            "worker_result_path": str(result_path),
            "worker_status": worker_result.get("status"),
        }
        session_file = save_session_record(device_id, day, session_payload)

        git_info = commit_device_changes(device_id, day=day, status=str(state.get("status")))
        append_event(
            device_id,
            {
                "type": "CYCLE_COMPLETED",
                "cycle_id": cycle_id,
                "day": day,
                "status": state.get("status"),
                "git": git_info,
            },
        )

        return {
            "device_id": device_id,
            "cycle_id": cycle_id,
            "day": day,
            "status": state.get("status"),
            "summary": state.get("last_summary"),
            "session_path": str(session_file),
            "git": git_info,
        }

    except (CodexRunFailure, Exception) as exc:
        _record_runtime_failure(state, str(exc))
        save_state(device_id, state)
        append_event(
            device_id,
            {
                "type": "CYCLE_FAILED",
                "cycle_id": cycle_id,
                "day": day,
                "error": str(exc),
            },
        )
        raise
