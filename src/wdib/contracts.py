"""Schema-backed contracts for WDIB control/worker exchange."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import PACKAGE_DIR

SCHEMA_DIR = PACKAGE_DIR / "schemas"


class ContractValidationError(ValueError):
    """Raised when payload fails schema validation."""


def _load_schema(schema_name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / schema_name
    if not path.exists():
        raise FileNotFoundError(f"Missing schema: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_with_jsonschema(payload: Any, schema: dict[str, Any]) -> list[str]:
    try:
        from jsonschema import Draft202012Validator  # type: ignore
    except Exception:
        return []

    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{location}: {error.message}")
    return errors


def _fallback_required_check(payload: Any, schema: dict[str, Any]) -> list[str]:
    if not isinstance(payload, dict):
        return ["<root>: payload must be an object"]

    missing = []
    for key in schema.get("required", []):
        if key not in payload:
            missing.append(f"<root>: missing required key '{key}'")
    return missing


def validate_payload(payload: Any, schema_name: str, *, label: str) -> None:
    schema = _load_schema(schema_name)

    errors = _validate_with_jsonschema(payload, schema)
    if not errors:
        errors = _fallback_required_check(payload, schema)

    if errors:
        joined = "; ".join(errors[:10])
        raise ContractValidationError(f"Invalid {label}: {joined}")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
