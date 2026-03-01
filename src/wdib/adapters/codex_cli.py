"""Adapter to execute WDIB work orders through Codex CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..contracts import ContractValidationError, load_json, validate_payload
from ..env import env_bool


class CodexRunFailure(RuntimeError):
    """Raised when Codex execution fails or does not produce a valid result."""


def _normalize_worker_result(payload: Any, work_order: dict[str, Any]) -> Any:
    """Coerce legacy/near-miss worker payloads into schema-compatible shape."""
    if not isinstance(payload, dict):
        return payload

    normalized: dict[str, Any] = {}
    allowed_top_level = {
        "schema_version",
        "cycle_id",
        "status",
        "summary",
        "becoming",
        "proposed_tasks",
        "task_updates",
        "proposed_hardware_requests",
        "incidents",
        "artifacts",
    }
    for key in allowed_top_level:
        if key in payload:
            normalized[key] = payload[key]

    normalized["schema_version"] = "1.0"
    normalized["cycle_id"] = str(normalized.get("cycle_id") or work_order.get("cycle_id") or "").strip()

    raw_status = str(normalized.get("status") or "").upper()
    status_map = {
        "SUCCESS": "COMPLETED",
        "DONE": "COMPLETED",
        "ERROR": "FAILED",
        "PENDING": "BLOCKED",
    }
    raw_status = status_map.get(raw_status, raw_status)
    if raw_status not in {"COMPLETED", "BLOCKED", "FAILED"}:
        raw_status = "BLOCKED"
    normalized["status"] = raw_status

    summary = str(normalized.get("summary") or "").strip()
    if not summary:
        summary = "Worker completed without a summary."
    normalized["summary"] = summary

    if "proposed_tasks" not in normalized and isinstance(payload.get("tasks"), list):
        proposed_tasks: list[dict[str, Any]] = []
        task_status_map = {"PENDING": "TODO"}
        for item in payload["tasks"]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "").strip()
            if not title:
                continue
            task_payload: dict[str, Any] = {"title": title}
            if item.get("description"):
                task_payload["description"] = str(item["description"])
            raw_task_status = str(item.get("status") or "").upper()
            raw_task_status = task_status_map.get(raw_task_status, raw_task_status)
            if raw_task_status in {"TODO", "IN_PROGRESS", "DONE", "BLOCKED"}:
                task_payload["status"] = raw_task_status
            if item.get("blocked_by"):
                task_payload["blocked_by"] = str(item["blocked_by"])
            if item.get("notes"):
                task_payload["notes"] = str(item["notes"])
            proposed_tasks.append(task_payload)
        if proposed_tasks:
            normalized["proposed_tasks"] = proposed_tasks

    if isinstance(payload.get("incidents"), list):
        normalized_incidents: list[dict[str, Any]] = []
        for item in payload["incidents"]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("id") or "WDIB incident").strip()
            summary_text = str(
                item.get("summary")
                or item.get("detail")
                or f"{title} reported by worker."
            ).strip()
            severity = str(item.get("severity") or "MEDIUM").upper()
            if severity not in {"LOW", "MEDIUM", "HIGH"}:
                severity = "MEDIUM"
            incident_status = str(item.get("status") or "OPEN").upper()
            if incident_status not in {"OPEN", "RESOLVED"}:
                incident_status = "OPEN"
            normalized_incidents.append(
                {
                    "title": title,
                    "summary": summary_text,
                    "severity": severity,
                    "status": incident_status,
                }
            )
        normalized["incidents"] = normalized_incidents

    return normalized


def _prompt_from_work_order(work_order: dict[str, Any]) -> str:
    return (
        "You are the WDIB worker plane.\n"
        "Execute the objective from the provided work order.\n"
        "You may inspect and modify code only inside allowed_paths.\n"
        "Use WDIB engineering discipline by default:\n"
        "1) For bugs/failures, find root cause before proposing fixes.\n"
        "2) For behavior/code changes, write or update tests first, then implement minimal code.\n"
        "3) Before claiming success, run concrete verification commands and report evidence.\n"
        "Include verification evidence in worker_result.summary.\n"
        "When finished, return ONLY the worker_result JSON.\n"
        "Do not invent fields. Follow schema_version 1.0 exactly.\n\n"
        "WORK_ORDER_JSON:\n"
        f"{json.dumps(work_order, indent=2, sort_keys=True)}\n"
    )


def _write_skip_result(work_order: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": "1.0",
        "cycle_id": work_order["cycle_id"],
        "status": "BLOCKED",
        "summary": "Codex execution skipped because WDIB_SKIP_CODEX=true.",
    }
    result_path = Path(work_order["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def execute_work_order(
    work_order: dict[str, Any],
    *,
    project_root: Path,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run codex exec and return (worker_result, run_metadata)."""
    if env_bool("WDIB_SKIP_CODEX", default=False):
        result = _write_skip_result(work_order)
        validate_payload(result, "worker_result.schema.json", label="worker_result")
        return result, {"mode": "skipped", "returncode": 0, "stdout": "", "stderr": ""}

    codex_bin = shutil.which("codex")
    if not codex_bin:
        raise CodexRunFailure("codex binary was not found in PATH")

    prompt = _prompt_from_work_order(work_order)
    result_path = Path(work_order["result_path"])
    sandbox_mode = (os.getenv("WDIB_CODEX_SANDBOX") or "workspace-write").strip()
    if sandbox_mode not in {"read-only", "workspace-write", "danger-full-access"}:
        sandbox_mode = "workspace-write"
    command = [
        codex_bin,
        "exec",
        "--sandbox",
        sandbox_mode,
        "--output-last-message",
        str(result_path),
        "--cd",
        str(project_root),
    ]
    codex_model = (os.getenv("WDIB_CODEX_MODEL") or "").strip()
    if codex_model:
        command.extend(["--model", codex_model])
    command.append(prompt)

    run_env = os.environ.copy()
    # Official Codex exec guidance favors CODEX_API_KEY in non-interactive runs.
    if not run_env.get("CODEX_API_KEY") and run_env.get("OPENAI_API_KEY"):
        run_env["CODEX_API_KEY"] = run_env["OPENAI_API_KEY"]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=run_env,
    )

    metadata = {
        "mode": "live",
        "returncode": completed.returncode,
        "stdout": (completed.stdout or "")[-4000:],
        "stderr": (completed.stderr or "")[-4000:],
    }

    if completed.returncode != 0:
        raise CodexRunFailure(
            f"codex exec failed ({completed.returncode}): {(completed.stderr or completed.stdout or '').strip()[:300]}"
        )

    if not result_path.exists():
        raise CodexRunFailure(f"worker result file not found: {result_path}")

    raw_result = result_path.read_text(encoding="utf-8")
    try:
        result_payload = json.loads(raw_result)
    except json.JSONDecodeError:
        # Some codex versions may include prose or code fences around JSON.
        start = raw_result.find("{")
        end = raw_result.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise CodexRunFailure("worker result output is not valid JSON")
        try:
            result_payload = json.loads(raw_result[start : end + 1])
        except json.JSONDecodeError as exc:
            raise CodexRunFailure(f"worker result output is not valid JSON: {exc}") from exc

    result_payload = _normalize_worker_result(result_payload, work_order)

    try:
        validate_payload(result_payload, "worker_result.schema.json", label="worker_result")
    except ContractValidationError as exc:
        raise CodexRunFailure(str(exc)) from exc

    return result_payload, metadata
