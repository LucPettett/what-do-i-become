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


def _prompt_from_work_order(work_order: dict[str, Any]) -> str:
    return (
        "You are the WDIB worker plane.\n"
        "Execute the objective from the provided work order.\n"
        "You may inspect and modify code only inside allowed_paths.\n"
        "When finished, write ONLY the worker_result JSON to result_path.\n"
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
    command = [
        codex_bin,
        "exec",
        "--sandbox",
        "workspace-write",
        "--ask-for-approval",
        "never",
        "--cd",
        str(project_root),
        prompt,
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=os.environ.copy(),
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

    result_path = Path(work_order["result_path"])
    if not result_path.exists():
        raise CodexRunFailure(f"worker result file not found: {result_path}")

    result_payload = load_json(result_path)
    try:
        validate_payload(result_payload, "worker_result.schema.json", label="worker_result")
    except ContractValidationError as exc:
        raise CodexRunFailure(str(exc)) from exc

    return result_payload, metadata
