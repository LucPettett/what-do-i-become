"""Persistence for WDIB per-device state and artifacts."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from ..contracts import dump_json, load_json, validate_payload
from ..paths import (
    DEVICES_DIR,
    EVENTS_FILE_NAME,
    PUBLIC_DAILY_DIR_NAME,
    PUBLIC_DIR_NAME,
    PUBLIC_STATUS_FILE_NAME,
    RUNTIME_DIR_NAME,
    SESSIONS_DIR_NAME,
    STATE_FILE_NAME,
    WORK_ORDERS_DIR_NAME,
    WORKER_RESULTS_DIR_NAME,
)


def _today() -> str:
    return date.today().isoformat()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def device_paths(device_id: str) -> dict[str, Path]:
    device_dir = DEVICES_DIR / device_id
    runtime_dir = device_dir / RUNTIME_DIR_NAME
    public_dir = device_dir / PUBLIC_DIR_NAME
    return {
        "device_dir": device_dir,
        "state": device_dir / STATE_FILE_NAME,
        "events": device_dir / EVENTS_FILE_NAME,
        "sessions": device_dir / SESSIONS_DIR_NAME,
        "runtime": runtime_dir,
        "work_orders": runtime_dir / WORK_ORDERS_DIR_NAME,
        "worker_results": runtime_dir / WORKER_RESULTS_DIR_NAME,
        "public_dir": public_dir,
        "public_daily": public_dir / PUBLIC_DAILY_DIR_NAME,
        "public_status": public_dir / PUBLIC_STATUS_FILE_NAME,
    }


def ensure_layout(device_id: str) -> dict[str, Path]:
    paths = device_paths(device_id)
    paths["device_dir"].mkdir(parents=True, exist_ok=True)
    paths["sessions"].mkdir(parents=True, exist_ok=True)
    paths["work_orders"].mkdir(parents=True, exist_ok=True)
    paths["worker_results"].mkdir(parents=True, exist_ok=True)
    paths["public_daily"].mkdir(parents=True, exist_ok=True)
    return paths


def default_state(device_id: str, spirit_path: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "device_id": device_id,
        "awoke_on": _today(),
        "day": 0,
        "purpose": {
            "becoming": "",
            "spirit_path": spirit_path,
        },
        "status": "ACTIVE",
        "tasks": [],
        "hardware_requests": [],
        "incidents": [],
        "artifacts": [],
        "last_summary": "",
    }


def load_state(device_id: str, spirit_path: str) -> dict[str, Any]:
    paths = ensure_layout(device_id)

    if not paths["state"].exists():
        state = default_state(device_id, spirit_path)
        save_state(device_id, state)
        append_event(
            device_id,
            {
                "ts": _now(),
                "type": "STATE_INITIALIZED",
                "message": "Created new WDIB state file.",
            },
        )
        return state

    state = load_json(paths["state"])
    validate_payload(state, "state.schema.json", label="state")
    return state


def save_state(device_id: str, state: dict[str, Any]) -> None:
    validate_payload(state, "state.schema.json", label="state")
    paths = ensure_layout(device_id)
    dump_json(paths["state"], state)


def append_event(device_id: str, event: dict[str, Any]) -> None:
    paths = ensure_layout(device_id)
    line = event.copy()
    line.setdefault("ts", _now())
    with paths["events"].open("a", encoding="utf-8") as handle:
        import json

        handle.write(json.dumps(line, sort_keys=True) + "\n")


def work_order_path(device_id: str, cycle_id: str) -> Path:
    paths = ensure_layout(device_id)
    return paths["work_orders"] / f"{cycle_id}.json"


def worker_result_path(device_id: str, cycle_id: str) -> Path:
    paths = ensure_layout(device_id)
    return paths["worker_results"] / f"{cycle_id}.json"


def save_work_order(device_id: str, cycle_id: str, payload: dict[str, Any]) -> Path:
    validate_payload(payload, "work_order.schema.json", label="work_order")
    path = work_order_path(device_id, cycle_id)
    dump_json(path, payload)
    return path


def save_worker_result(device_id: str, cycle_id: str, payload: dict[str, Any]) -> Path:
    validate_payload(payload, "worker_result.schema.json", label="worker_result")
    path = worker_result_path(device_id, cycle_id)
    dump_json(path, payload)
    return path


def save_session_record(device_id: str, day: int, payload: dict[str, Any]) -> Path:
    paths = ensure_layout(device_id)
    run_date = payload.get("date") or _today()
    filename = f"day_{day:03d}_{run_date}.json"
    path = paths["sessions"] / filename
    dump_json(path, payload)
    return path


def save_public_status(device_id: str, payload: dict[str, Any]) -> Path:
    paths = ensure_layout(device_id)
    path = paths["public_status"]
    dump_json(path, payload)
    return path


def save_public_daily_summary(device_id: str, day: int, run_date: str, markdown: str) -> Path:
    paths = ensure_layout(device_id)
    filename = f"day_{day:03d}_{run_date}.md"
    path = paths["public_daily"] / filename
    path.write_text(markdown, encoding="utf-8")
    return path
