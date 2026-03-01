"""Human instruction inbox for WDIB."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..storage.repository import device_paths, ensure_layout


def enqueue_human_message(device_id: str, text: str) -> Path:
    """Write a pending human message for the next runtime tick."""
    cleaned = str(text or "").strip()
    if not cleaned:
        raise ValueError("human message text cannot be empty")
    paths = ensure_layout(device_id)
    payload = f"ts={datetime.now().isoformat(timespec='seconds')}\n{cleaned}\n"
    target = paths["human_message"]
    target.write_text(payload, encoding="utf-8")
    return target


def load_and_clear_human_message(device_id: str) -> str:
    """Return pending message text and remove it from inbox."""
    path = device_paths(device_id)["human_message"]
    if not path.exists():
        return ""
    raw = path.read_text(encoding="utf-8")
    path.unlink(missing_ok=True)

    lines = [line.rstrip() for line in raw.splitlines()]
    if lines and lines[0].startswith("ts="):
        lines = lines[1:]
    return "\n".join(lines).strip()


def is_terminate_command(message_text: str) -> bool:
    """Heuristic parser for human stop/terminate instructions."""
    lowered = str(message_text or "").strip().lower()
    if not lowered:
        return False
    markers = (
        "terminate",
        "shutdown",
        "shut down",
        "power down",
        "stop this device",
        "stop device",
        "kill command",
        "kill wdib",
        "goodbye",
    )
    return any(marker in lowered for marker in markers)
