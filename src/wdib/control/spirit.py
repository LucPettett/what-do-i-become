"""SPIRIT.md loader for WDIB purpose context."""

from __future__ import annotations

from ..paths import SPIRIT_FILE


def load_spirit_text() -> str:
    if not SPIRIT_FILE.exists():
        return ""
    return SPIRIT_FILE.read_text(encoding="utf-8")
