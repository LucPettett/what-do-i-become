"""WDIB cycle runtime."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .adapters.codex_cli import CodexRunFailure, execute_work_order
from .adapters.git_repo import commit_device_changes
from .control.hardware import probe_hardware_requests
from .control.human_messages import is_terminate_command, load_and_clear_human_message
from .control.planner import plan_work_order
from .control.reducer import apply_worker_result
from .control.mission import load_mission_text
from .env import load_dotenv, resolve_device_id
from .notifications.router import send_cycle_notifications, send_failure_notifications
from .paths import PROJECT_ROOT, MISSION_FILE
from .policy.safety import codex_timeout_seconds, command_timeout_seconds
from .publication import build_public_daily_summary, build_public_status
from .storage.repository import (
    append_event,
    device_paths,
    load_state,
    save_public_daily_summary,
    save_public_status,
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


_META_BECOMING_MARKERS = (
    "wdib",
    "control-plane",
    "control plane",
    "worker_result",
    "schema",
    "task machinery",
    "verified tasks",
    "runtime reliability",
    "autonomous loop",
)

_MISSION_DISCOVERY_MIN_DAY_FOR_BECOMING = 3


def _looks_framework_internal_becoming(text: str) -> bool:
    value = str(text or "").strip().lower()
    if not value:
        return False
    return any(marker in value for marker in _META_BECOMING_MARKERS)


def _clear_becoming_from_state_when_mission_unknown(
    state: dict[str, Any],
    *,
    mission_text: str,
) -> dict[str, Any] | None:
    if str(mission_text or "").strip():
        return None
    existing = str(state.get("purpose", {}).get("becoming") or "").strip()
    if not existing:
        return None
    state_day = int(state.get("day") or 0)
    if state_day < _MISSION_DISCOVERY_MIN_DAY_FOR_BECOMING:
        state.setdefault("purpose", {})["becoming"] = ""
        return {
            "type": "BECOMING_CLEARED",
            "from": existing,
            "reason": (
                "Mission is unknown and discovery is still in progress; "
                "becoming remains unset until sustained evidence across multiple cycles."
            ),
        }
    if not _looks_framework_internal_becoming(existing):
        return None
    state.setdefault("purpose", {})["becoming"] = ""
    return {
        "type": "BECOMING_CLEARED",
        "from": existing,
        "reason": "MISSION.md is empty and becoming was framework-internal; continue mission discovery from external evidence.",
    }


def _reject_becoming_when_mission_unknown(
    worker_result: dict[str, Any],
    *,
    mission_text: str,
    day: int,
) -> dict[str, Any] | None:
    if str(mission_text or "").strip():
        return None
    candidate = str(worker_result.get("becoming") or "").strip()
    if not candidate:
        return None
    if _looks_framework_internal_becoming(candidate):
        worker_result.pop("becoming", None)
        return {
            "type": "BECOMING_REJECTED",
            "candidate": candidate,
            "reason": "MISSION.md is empty and candidate becoming was framework-internal; propose human/environment outcomes instead.",
        }
    if int(day) < _MISSION_DISCOVERY_MIN_DAY_FOR_BECOMING:
        worker_result.pop("becoming", None)
        return {
            "type": "BECOMING_REJECTED",
            "candidate": candidate,
            "reason": (
                f"Mission is unknown and day {int(day):03d} is too early to lock becoming; "
                "continue evidence-building across multiple cycles first."
            ),
        }
    return None


def _mission_unknown(*, mission_text: str) -> bool:
    return not str(mission_text or "").strip()


def _mission_unknown_event(day: int) -> dict[str, Any]:
    return {
        "type": "MISSION_UNKNOWN",
        "day": int(day),
        "reason": (
            "MISSION.md is not set; keep mission discovery active over multiple cycles. "
            "Build capabilities, gather evidence, and avoid premature mission locking."
        ),
    }


def _append_notification_events(
    device_id: str,
    cycle_id: str,
    day: int,
    results: list[dict[str, Any]],
) -> None:
    for result in results:
        channel = str(result.get("channel") or "unknown")
        sent = bool(result.get("sent"))
        event_type = "NOTIFICATION_SENT" if sent else "NOTIFICATION_FAILED"
        payload = {
            "type": event_type,
            "cycle_id": cycle_id,
            "day": day,
            "channel": channel,
        }
        if sent:
            if "status_code" in result:
                payload["status_code"] = result.get("status_code")
        else:
            payload["reason"] = str(result.get("reason") or "unknown")
        append_event(device_id, payload)


def run_tick() -> dict[str, Any]:
    load_dotenv()

    device_id = resolve_device_id()
    mission_text = load_mission_text()
    mission_path = str(MISSION_FILE)
    state = load_state(device_id, mission_path=mission_path)
    pre_cycle_event = _clear_becoming_from_state_when_mission_unknown(
        state,
        mission_text=mission_text,
    )
    if pre_cycle_event:
        save_state(device_id, state)
        append_event(device_id, pre_cycle_event)

    pending_human_message = load_and_clear_human_message(device_id)
    if pending_human_message:
        append_event(
            device_id,
            {
                "type": "HUMAN_MESSAGE_RECEIVED",
                "message": pending_human_message[:500],
            },
        )

    if str(state.get("status") or "").upper() == "TERMINATED" and not pending_human_message:
        return {
            "device_id": device_id,
            "status": "TERMINATED",
            "skipped": True,
            "summary": "Device is terminated; no cycle was run.",
        }

    previous_day = int(state.get("day") or 0)
    day = previous_day + 1
    cycle_id = _cycle_id(day)
    started_at = datetime.now()
    run_date = started_at.date().isoformat()

    append_event(
        device_id,
        {
            "type": "CYCLE_STARTED",
            "cycle_id": cycle_id,
            "day": day,
            "status": state.get("status"),
        },
    )
    if _mission_unknown(mission_text=mission_text):
        unknown_event = _mission_unknown_event(day)
        unknown_event["cycle_id"] = cycle_id
        append_event(device_id, unknown_event)

    try:
        if pending_human_message and is_terminate_command(pending_human_message):
            state["status"] = "TERMINATED"
            state["day"] = day
            state.setdefault("purpose", {})["becoming"] = "Gracefully conclude this mission run and hand over cleanly."
            state["last_summary"] = (
                "Received human termination instruction and gracefully ended this run. "
                "Goodbye for now."
            )
            save_state(device_id, state)
            append_event(
                device_id,
                {
                    "type": "HUMAN_COMMAND_TERMINATE",
                    "cycle_id": cycle_id,
                    "day": day,
                    "message": pending_human_message[:500],
                },
            )

            session_payload = {
                "date": run_date,
                "cycle_id": cycle_id,
                "day": day,
                "status": state.get("status"),
                "summary": state.get("last_summary", ""),
                "work_order_path": "",
                "worker_result_path": "",
                "worker_status": "TERMINATED",
            }
            session_file = save_session_record(device_id, day, session_payload)

            public_status_payload = build_public_status(
                device_id=device_id,
                cycle_id=cycle_id,
                day=day,
                state=state,
                worker_status="TERMINATED",
                mission_text=mission_text,
                summary_hint=str(state.get("last_summary") or ""),
                objective_hint="Human requested device termination.",
                now=started_at,
            )
            public_status_file = save_public_status(device_id, public_status_payload)
            public_daily_summary = build_public_daily_summary(
                status_payload=public_status_payload,
                objective="Human requested device termination.",
                summary_hint=str(state.get("last_summary") or ""),
                now=started_at,
            )
            public_daily_file = save_public_daily_summary(device_id, day, run_date, public_daily_summary)

            git_info = commit_device_changes(
                device_id,
                day=day,
                status=str(state.get("status")),
                publish_paths=[str(public_status_file), str(public_daily_file)],
            )
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

            notification_results = send_cycle_notifications(
                status_payload=public_status_payload,
                git_info=git_info,
                run_date=run_date,
            )
            _append_notification_events(device_id, cycle_id, day, notification_results)

            return {
                "device_id": device_id,
                "cycle_id": cycle_id,
                "day": day,
                "status": state.get("status"),
                "summary": state.get("last_summary"),
                "session_path": str(session_file),
                "public_status_path": str(public_status_file),
                "public_daily_path": str(public_daily_file),
                "git": git_info,
                "notifications": notification_results,
                "terminated": True,
            }

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
            mission_text=mission_text,
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
        rejected_becoming_event = _reject_becoming_when_mission_unknown(
            worker_result,
            mission_text=mission_text,
            day=day,
        )
        if rejected_becoming_event:
            rejected_becoming_event["cycle_id"] = cycle_id
            append_event(device_id, rejected_becoming_event)
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
            "date": run_date,
            "cycle_id": cycle_id,
            "day": day,
            "status": state.get("status"),
            "summary": state.get("last_summary", ""),
            "work_order_path": str(work_order_file),
            "worker_result_path": str(result_path),
            "worker_status": worker_result.get("status"),
        }
        session_file = save_session_record(device_id, day, session_payload)

        public_status_payload = build_public_status(
            device_id=device_id,
            cycle_id=cycle_id,
            day=day,
            state=state,
            worker_status=str(worker_result.get("status") or "UNKNOWN"),
            mission_text=mission_text,
            summary_hint=str(state.get("last_summary") or ""),
            objective_hint=str(work_order.get("objective") or ""),
            now=started_at,
        )
        public_status_file = save_public_status(device_id, public_status_payload)
        public_daily_summary = build_public_daily_summary(
            status_payload=public_status_payload,
            objective=str(work_order.get("objective") or ""),
            summary_hint=str(state.get("last_summary") or ""),
            now=started_at,
        )
        public_daily_file = save_public_daily_summary(device_id, day, run_date, public_daily_summary)

        git_info = commit_device_changes(
            device_id,
            day=day,
            status=str(state.get("status")),
            publish_paths=[str(public_status_file), str(public_daily_file)],
        )
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

        notification_results = send_cycle_notifications(
            status_payload=public_status_payload,
            git_info=git_info,
            run_date=run_date,
        )
        _append_notification_events(device_id, cycle_id, day, notification_results)

        return {
            "device_id": device_id,
            "cycle_id": cycle_id,
            "day": day,
            "status": state.get("status"),
            "summary": state.get("last_summary"),
            "session_path": str(session_file),
            "public_status_path": str(public_status_file),
            "public_daily_path": str(public_daily_file),
            "git": git_info,
            "notifications": notification_results,
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
        failure_notification_results = send_failure_notifications(
            device_id=device_id,
            cycle_id=cycle_id,
            day=day,
            ts=datetime.now(),
        )
        _append_notification_events(device_id, cycle_id, day, failure_notification_results)
        raise
