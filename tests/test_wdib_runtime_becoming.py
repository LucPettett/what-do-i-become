#!/usr/bin/env python3
"""Tests for WDIB becoming normalization rules."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wdib.runtime import (  # noqa: E402
    _clear_framework_becoming_from_state_when_spirit_empty,
    _reject_framework_becoming_when_spirit_empty,
)


class RuntimeBecomingTests(unittest.TestCase):
    def test_rejects_framework_becoming_when_spirit_is_empty(self) -> None:
        worker_result = {
            "schema_version": "1.0",
            "cycle_id": "cycle-001",
            "status": "COMPLETED",
            "summary": "ok",
            "becoming": "Become a reliable autonomous WDIB loop.",
        }
        event = _reject_framework_becoming_when_spirit_empty(worker_result, spirit_text="")
        self.assertIsNotNone(event)
        self.assertNotIn("becoming", worker_result)

    def test_keeps_becoming_when_spirit_has_mission(self) -> None:
        worker_result = {
            "schema_version": "1.0",
            "cycle_id": "cycle-001",
            "status": "COMPLETED",
            "summary": "ok",
            "becoming": "Improve local litter hotspot detection.",
        }
        event = _reject_framework_becoming_when_spirit_empty(
            worker_result,
            spirit_text="## Mission\nHelp clean the beach.",
        )
        self.assertIsNone(event)
        self.assertEqual(worker_result.get("becoming"), "Improve local litter hotspot detection.")

    def test_clears_legacy_framework_becoming_when_spirit_empty(self) -> None:
        state = {"purpose": {"becoming": "Build a WDIB control-plane loop."}}
        event = _clear_framework_becoming_from_state_when_spirit_empty(state, spirit_text="")
        self.assertIsNotNone(event)
        self.assertEqual(state["purpose"]["becoming"], "")


if __name__ == "__main__":
    unittest.main()
