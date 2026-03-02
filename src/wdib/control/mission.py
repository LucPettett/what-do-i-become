"""MISSION.md loader for WDIB purpose context."""

from __future__ import annotations

from ..paths import MISSION_FILE


def load_mission_text() -> str:
    if not MISSION_FILE.exists():
        return ""
    return MISSION_FILE.read_text(encoding="utf-8")
