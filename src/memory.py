#!/usr/bin/env python3
"""Persistence for per-device state under devices/<uuid>/."""

from __future__ import annotations

import glob
import os
import platform
import shutil
import subprocess
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

FRAMEWORK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FRAMEWORK_DIR.parent
DEVICES_DIR = PROJECT_ROOT / "devices"
FRAMEWORK_SPIRIT_FILE = FRAMEWORK_DIR / "SPIRIT.md"
LEGACY_SPIRIT_FILE = PROJECT_ROOT / "SPIRIT.md"
ENV_FILE = FRAMEWORK_DIR / ".env"
MAX_NOTES_CHARS = 3000

ALLOWED_STATUSES = {
    "FIRST_RUN",
    "EXPLORING",
    "WRITING_CODE",
    "VERIFYING_PART",
    "AWAITING_PART",
    "ERROR",
}

PART_STATUSES = {"REQUESTED", "INSTALLED", "VERIFIED"}


def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, _str_representer)


def _parse_env_file(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    if not path.exists():
        return parsed
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        parsed[key.strip()] = value.strip()
    return parsed


def _normalize_uuid(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return str(uuid.UUID(raw.strip()))
    except (ValueError, AttributeError, TypeError):
        return None


def resolve_device_id() -> str:
    env_value = _normalize_uuid(os.environ.get("WDIB_DEVICE_ID"))
    if env_value:
        return env_value

    from_env_file = _normalize_uuid(_parse_env_file(ENV_FILE).get("WDIB_DEVICE_ID"))
    if from_env_file:
        return from_env_file

    raise RuntimeError(
        "WDIB_DEVICE_ID is not configured. Run src/setup.sh first to awaken this device."
    )


def short_device_id(device_id: str | None = None) -> str:
    resolved = device_id or resolve_device_id()
    return resolved[:8]


def _device_paths() -> dict[str, Path]:
    device_id = resolve_device_id()
    device_dir = DEVICES_DIR / device_id
    return {
        "device_id": device_id,
        "device_dir": device_dir,
        "device_yaml": device_dir / "device.yaml",
        "notes": device_dir / "notes.md",
        "human_message": device_dir / "human_message.txt",
        "sessions": device_dir / "sessions",
    }


def get_human_message_path() -> str:
    return str(_device_paths()["human_message"])


def _detect_board() -> str:
    device_tree_model = Path("/proc/device-tree/model")
    if device_tree_model.exists():
        try:
            raw = device_tree_model.read_bytes().replace(b"\x00", b"")
            decoded = raw.decode("utf-8", errors="ignore").strip()
            if decoded:
                return decoded
        except OSError:
            pass

    if platform.system() == "Darwin":
        try:
            model = subprocess.check_output(["sysctl", "-n", "hw.model"], text=True).strip()
            if model:
                return model
        except Exception:
            pass

    return platform.node() or platform.machine() or "unknown"


def _detect_ram() -> str:
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        total_gib = (page_size * phys_pages) / float(1024**3)
        return f"{total_gib:.1f} GB"
    except (ValueError, OSError, AttributeError):
        return "unknown"


def _detect_os() -> str:
    os_release = Path("/etc/os-release")
    if os_release.exists():
        for raw_line in os_release.read_text(encoding="utf-8").splitlines():
            if raw_line.startswith("PRETTY_NAME="):
                return raw_line.split("=", 1)[1].strip().strip('"')
    return f"{platform.system()} {platform.release()}".strip()


def discover_hardware() -> dict[str, str]:
    return {
        "board": _detect_board(),
        "ram": _detect_ram(),
        "os": _detect_os(),
        "arch": platform.machine() or "unknown",
    }


def _default_state(device_id: str) -> dict[str, Any]:
    return {
        "id": device_id,
        "awoke": date.today().isoformat(),
        "day": 0,
        "last_session": None,
        "hardware": discover_hardware(),
        "becoming": "",
        "status": "FIRST_RUN",
        "parts": [],
        "part_requested": None,
        "last_summary": "",
    }


def _normalize_status(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in ALLOWED_STATUSES:
        return text

    legacy_phase_map = {
        "WAITING": "AWAITING_PART",
        "EXPLORING": "EXPLORING",
    }
    if text in legacy_phase_map:
        return legacy_phase_map[text]

    return "ERROR"


def _normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_hardware(value: Any) -> dict[str, str]:
    default = discover_hardware()
    if not isinstance(value, dict):
        return default
    return {
        "board": str(value.get("board") or default["board"]).strip(),
        "ram": str(value.get("ram") or default["ram"]).strip(),
        "os": str(value.get("os") or default["os"]).strip(),
        "arch": str(value.get("arch") or default["arch"]).strip(),
    }


def _normalize_part_status(value: Any, part: dict[str, Any]) -> str:
    text = str(value or "").strip().upper()
    if text in PART_STATUSES:
        return text
    if part.get("verified_on"):
        return "VERIFIED"
    if part.get("installed_on"):
        return "INSTALLED"
    return "REQUESTED"


def _normalize_parts(parts: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if not isinstance(parts, list):
        return normalized

    for item in parts:
        if not isinstance(item, dict):
            continue
        part: dict[str, Any] = {
            "name": str(item.get("name") or "").strip(),
            "reason": str(item.get("reason") or item.get("rationale") or "").strip(),
            "details": str(item.get("details") or item.get("description") or "").strip(),
            "requested_on": _normalize_date(item.get("requested_on") or item.get("date_ordered")),
            "installed_on": _normalize_date(item.get("installed_on")),
            "verified_on": _normalize_date(item.get("verified_on") or item.get("date_confirmed")),
            "verification": str(item.get("verification") or "").strip(),
            "detection_hint": str(item.get("detection_hint") or "").strip(),
            "estimated_price": str(item.get("estimated_price") or "").strip(),
        }
        part["status"] = _normalize_part_status(item.get("status"), part)
        if part["name"]:
            normalized.append(part)
    return normalized


def _normalize_part_requested(part_requested: Any, legacy_pending: Any = None) -> dict[str, str] | None:
    candidate = part_requested if isinstance(part_requested, dict) else None
    if candidate is None and isinstance(legacy_pending, dict):
        candidate = {
            "name": legacy_pending.get("part_name"),
            "reason": legacy_pending.get("rationale") or legacy_pending.get("description"),
            "date": legacy_pending.get("date_ordered"),
        }

    if not isinstance(candidate, dict):
        return None

    name = str(candidate.get("name") or candidate.get("part_name") or "").strip()
    reason = str(candidate.get("reason") or candidate.get("rationale") or "").strip()
    req_date = str(candidate.get("date") or candidate.get("date_ordered") or "").strip()
    if not name:
        return None

    return {"name": name, "reason": reason, "date": req_date or date.today().isoformat()}


def _normalize_state(state: Any, device_id: str) -> dict[str, Any]:
    base = _default_state(device_id)
    source = state if isinstance(state, dict) else {}

    base["id"] = str(source.get("id") or device_id).strip() or device_id
    base["awoke"] = str(source.get("awoke") or source.get("first_boot") or base["awoke"]).strip()

    day_value = source.get("day", source.get("total_sessions", base["day"]))
    try:
        base["day"] = max(0, int(day_value))
    except (TypeError, ValueError):
        base["day"] = 0

    base["last_session"] = _normalize_date(source.get("last_session"))
    base["hardware"] = _normalize_hardware(source.get("hardware"))

    becoming = source.get("becoming")
    if becoming is None:
        becoming = source.get("spirit")
    base["becoming"] = str(becoming or "").strip()

    if "status" in source:
        status_input = source.get("status")
    elif "phase" in source:
        status_input = source.get("phase")
    else:
        status_input = base["status"]
    base["status"] = _normalize_status(status_input)

    parts = _normalize_parts(source.get("parts", source.get("parts_installed")))
    base["parts"] = parts

    base["part_requested"] = _normalize_part_requested(
        source.get("part_requested"),
        legacy_pending=source.get("pending_order"),
    )

    if base["part_requested"] and base["status"] not in {"AWAITING_PART", "VERIFYING_PART"}:
        base["status"] = "AWAITING_PART"
    if not base["part_requested"] and base["status"] == "AWAITING_PART":
        base["status"] = "EXPLORING"

    base["last_summary"] = str(source.get("last_summary") or "").strip()
    return base


def _ensure_dirs() -> None:
    paths = _device_paths()
    paths["device_dir"].mkdir(parents=True, exist_ok=True)
    paths["sessions"].mkdir(parents=True, exist_ok=True)


def load_state() -> dict[str, Any]:
    _ensure_dirs()
    paths = _device_paths()

    raw: Any = {}
    if paths["device_yaml"].exists():
        raw = yaml.safe_load(paths["device_yaml"].read_text(encoding="utf-8")) or {}

    state = _normalize_state(raw, resolve_device_id())

    if not paths["notes"].exists():
        paths["notes"].write_text("", encoding="utf-8")

    save_state(state)
    return state


def save_state(state: dict[str, Any]) -> None:
    _ensure_dirs()
    paths = _device_paths()
    normalized = _normalize_state(state, resolve_device_id())
    with paths["device_yaml"].open("w", encoding="utf-8") as handle:
        yaml.dump(
            normalized,
            handle,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )


def load_notes() -> str:
    paths = _device_paths()
    if paths["notes"].exists():
        return paths["notes"].read_text(encoding="utf-8")
    return ""


def save_notes_file(content: str) -> int:
    paths = _device_paths()
    if len(content) > MAX_NOTES_CHARS:
        content = content[:MAX_NOTES_CHARS] + "\n\n[TRUNCATED TO FIT BUDGET]"
    paths["notes"].write_text(content, encoding="utf-8")
    return len(content)


def load_spirit() -> str:
    if FRAMEWORK_SPIRIT_FILE.exists():
        return FRAMEWORK_SPIRIT_FILE.read_text(encoding="utf-8")
    if LEGACY_SPIRIT_FILE.exists():
        return LEGACY_SPIRIT_FILE.read_text(encoding="utf-8")
    return ""


def collect_inventory_snapshot() -> dict[str, Any]:
    tracked_commands = [
        "python3",
        "pip3",
        "git",
        "curl",
        "wget",
        "apt-get",
        "brew",
        "docker",
        "ffmpeg",
        "node",
        "npm",
        "uv",
        "systemctl",
    ]

    device_patterns = [
        "/dev/video*",
        "/dev/i2c-*",
        "/dev/spidev*",
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
        "/dev/serial*",
        "/dev/snd/*",
    ]

    devices: list[str] = []
    for pattern in device_patterns:
        devices.extend(glob.glob(pattern))

    detected_devices = sorted(set(devices))
    if len(detected_devices) > 40:
        detected_devices = detected_devices[:40]

    return {
        "observed_at": datetime.now().isoformat(timespec="seconds"),
        "hostname": platform.node(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "available_commands": sorted(cmd for cmd in tracked_commands if shutil.which(cmd)),
        "detected_devices": detected_devices,
    }


def load_session_summaries(last_n: int = 10) -> list[dict[str, Any]]:
    paths = _device_paths()
    paths["sessions"].mkdir(parents=True, exist_ok=True)

    files = sorted(paths["sessions"].glob("day_*.yaml"))
    summaries: list[dict[str, Any]] = []

    for filepath in files[-last_n:]:
        try:
            data = yaml.safe_load(filepath.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        summary = str(data.get("summary") or "").strip()
        if not summary:
            continue
        summaries.append(
            {
                "date": data.get("date", "?"),
                "session_number": data.get("session_number", "?"),
                "summary": summary,
            }
        )

    return summaries


def save_session(session_log: dict[str, Any]) -> str:
    paths = _device_paths()
    paths["sessions"].mkdir(parents=True, exist_ok=True)

    day_number = int(session_log.get("session_number", 0))
    run_date = str(session_log.get("date") or date.today().isoformat())
    filename = f"day_{day_number:03d}_{run_date}.yaml"
    filepath = paths["sessions"] / filename

    with filepath.open("w", encoding="utf-8") as handle:
        yaml.dump(
            session_log,
            handle,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )

    return str(filepath)


def generate_summary(generate_text, session_log: dict[str, Any]) -> str:
    """Ask the LLM to summarise a session for future context."""
    lines: list[str] = []

    for msg in session_log.get("conversation", []):
        role = msg.get("role", "?")
        msg_type = msg.get("type", "")

        if msg_type == "tool_call":
            args_preview = str(msg.get("arguments", ""))[:200]
            lines.append(f"[CALLED {msg.get('tool')}] {args_preview}")
            continue

        if msg_type == "tool_result":
            output = msg.get("output", {})
            if isinstance(output, dict):
                preview = output.get("output", output.get("message", str(output)))[:300]
            else:
                preview = str(output)[:300]
            lines.append(f"[RESULT {msg.get('tool')}] {preview}")
            continue

        content = str(msg.get("content", ""))[:400]
        lines.append(f"[{role.upper()}] {content}")

    transcript = "\n".join(lines)
    if len(transcript) > 6000:
        transcript = transcript[:6000] + "\n[TRANSCRIPT TRUNCATED FOR SUMMARY]"

    return generate_text(
        instructions=(
            "Summarise this what-do-i-become session in 2-3 concise paragraphs. "
            "Include: discoveries, commands run, decisions made, part requests or verifications, "
            "and the ending status. Be factual and specific."
        ),
        user_prompt=f"Session transcript:\n\n{transcript}",
    )
