"""Safety/policy defaults for WDIB control plane."""

from __future__ import annotations

from ..env import env_int


def codex_timeout_seconds() -> int:
    return max(60, env_int("WDIB_CODEX_TIMEOUT_SECONDS", 1200))


def command_timeout_seconds() -> int:
    return max(5, env_int("WDIB_HW_COMMAND_TIMEOUT_SECONDS", 20))


def work_order_constraints() -> list[str]:
    return [
        "Work only inside allowed_paths.",
        "Do not bypass hardware verification semantics. Hardware requests are complete only when machine-observed detection and verification pass.",
        "Persist outcomes in the worker result contract only.",
        "Favor minimal, testable changes and explicit evidence.",
    ]
