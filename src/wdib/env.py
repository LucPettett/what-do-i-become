"""Environment helpers for WDIB."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from .paths import DEVICE_ID_FILE, ENV_FILE


def load_dotenv() -> None:
    """Load key/value pairs from src/.env into process env if unset."""
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _normalize_uuid(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return str(uuid.UUID(raw.strip()))
    except (ValueError, AttributeError, TypeError):
        return None


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def resolve_device_id() -> str:
    """Resolve (or lazily create) the WDIB device UUID."""
    from_env = _normalize_uuid(os.environ.get("WDIB_DEVICE_ID"))
    if from_env:
        return from_env

    from_env_file = _normalize_uuid(_parse_env_file(ENV_FILE).get("WDIB_DEVICE_ID"))
    if from_env_file:
        os.environ.setdefault("WDIB_DEVICE_ID", from_env_file)
        return from_env_file

    if DEVICE_ID_FILE.exists():
        from_device_file = _normalize_uuid(DEVICE_ID_FILE.read_text(encoding="utf-8").strip())
        if from_device_file:
            os.environ.setdefault("WDIB_DEVICE_ID", from_device_file)
            return from_device_file

    generated = str(uuid.uuid4())
    DEVICE_ID_FILE.write_text(generated, encoding="utf-8")
    os.environ.setdefault("WDIB_DEVICE_ID", generated)
    return generated
