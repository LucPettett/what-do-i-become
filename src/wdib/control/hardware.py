"""Hardware auto-detection and verification transitions."""

from __future__ import annotations

import glob
import subprocess
from datetime import date
from pathlib import Path
from typing import Any


def _today() -> str:
    return date.today().isoformat()


def _append_note(existing: str, note: str) -> str:
    prefix = existing.strip()
    line = f"[{_today()}] {note}"
    if not prefix:
        return line
    return f"{prefix}\n{line}"


def _run_shell(command: str, timeout_seconds: int) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout_seconds}s"
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)

    output = (result.stdout or "")
    if result.stderr:
        output = f"{output}\n{result.stderr}".strip()
    return result.returncode == 0, output.strip()


def _detect(detection: dict[str, Any], timeout_seconds: int) -> tuple[bool, str]:
    kind = str(detection.get("kind") or "").strip()
    value = str(detection.get("value") or "").strip()

    if kind == "path_exists":
        return Path(value).exists(), f"path_exists({value})"

    if kind == "glob_exists":
        matches = glob.glob(value)
        return bool(matches), f"glob_exists({value}) -> {len(matches)} match(es)"

    if kind == "command_success":
        ok, output = _run_shell(value, timeout_seconds)
        return ok, f"command_success({value}) -> {output[:200]}"

    if kind == "lsusb_contains":
        ok, output = _run_shell("lsusb", timeout_seconds)
        if not ok:
            return False, f"lsusb failed: {output[:200]}"
        found = value.lower() in output.lower()
        return found, f"lsusb_contains({value})"

    return False, f"unknown detection kind: {kind}"


def probe_hardware_requests(state: dict[str, Any], timeout_seconds: int) -> list[dict[str, Any]]:
    """Advance OPEN/DETECTED requests based on machine-observed signals."""
    events: list[dict[str, Any]] = []
    requests = state.get("hardware_requests", [])
    today = _today()

    for request in requests:
        status = str(request.get("status") or "OPEN")
        if status in {"VERIFIED", "FAILED"}:
            continue

        request_id = str(request.get("id") or "")
        request["last_checked_on"] = today

        detected, evidence = _detect(request.get("detection") or {}, timeout_seconds)
        previous_status = status

        if detected:
            if status == "OPEN":
                request["status"] = "DETECTED"
                request["detected_on"] = today
                events.append(
                    {
                        "type": "HARDWARE_STATUS_CHANGED",
                        "request_id": request_id,
                        "from": previous_status,
                        "to": "DETECTED",
                        "evidence": evidence,
                    }
                )
                status = "DETECTED"

            verify_command = str(request.get("verify_command") or "").strip()
            if verify_command:
                ok, verify_output = _run_shell(verify_command, timeout_seconds)
                if ok:
                    request["status"] = "VERIFIED"
                    request["verified_on"] = today
                    request["notes"] = _append_note(
                        str(request.get("notes") or ""),
                        f"Verification passed: {verify_command}",
                    )
                    events.append(
                        {
                            "type": "HARDWARE_STATUS_CHANGED",
                            "request_id": request_id,
                            "from": status,
                            "to": "VERIFIED",
                            "evidence": verify_output[:240],
                        }
                    )
                else:
                    request["verify_failures"] = int(request.get("verify_failures") or 0) + 1
                    request["notes"] = _append_note(
                        str(request.get("notes") or ""),
                        f"Verification failed ({verify_command}): {verify_output[:240]}",
                    )
                    events.append(
                        {
                            "type": "HARDWARE_VERIFICATION_FAILED",
                            "request_id": request_id,
                            "verify_failures": int(request.get("verify_failures") or 0),
                            "evidence": verify_output[:240],
                        }
                    )
            else:
                request["status"] = "VERIFIED"
                request["verified_on"] = today
                events.append(
                    {
                        "type": "HARDWARE_STATUS_CHANGED",
                        "request_id": request_id,
                        "from": status,
                        "to": "VERIFIED",
                        "evidence": "No verify_command provided; detection accepted as verification.",
                    }
                )

        elif status == "DETECTED":
            request["status"] = "OPEN"
            request["detected_on"] = None
            request["notes"] = _append_note(
                str(request.get("notes") or ""),
                "Detection signal no longer present; moved back to OPEN.",
            )
            events.append(
                {
                    "type": "HARDWARE_STATUS_CHANGED",
                    "request_id": request_id,
                    "from": "DETECTED",
                    "to": "OPEN",
                    "evidence": evidence,
                }
            )

    return events
