#!/usr/bin/env python3
"""Tests for WDIB Slack message formatting."""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wdib.adapters.slack_webhook import _build_cycle_text  # noqa: E402


class SlackWebhookFormattingTests(unittest.TestCase):
    def test_human_message_style_is_default(self) -> None:
        status_payload = {
            "device_id_short": "abcd1234",
            "day": 2,
            "status": "ACTIVE",
            "worker_status": "COMPLETED",
            "cycle_id": "cycle-002-20260301T112400",
            "purpose": "Help clean local beaches by reducing litter hotspots.",
            "becoming": "Improve hotspot detection and daily clean-up guidance.",
            "counts": {
                "tasks": {"todo": 2, "in_progress": 1, "done": 1, "blocked": 0},
                "hardware_requests": {"open": 0, "detected": 0, "verified": 0, "failed": 0},
                "incidents_open": 0,
            },
        }
        with mock.patch.dict(os.environ, {}, clear=False):
            text = _build_cycle_text(status_payload, {"pushed": True}, "2026-03-01")

        self.assertIn("I awoke and", text)
        self.assertIn("Stayed grounded in this purpose", text)
        self.assertIn("Took this next becoming step", text)
        self.assertIn("Shared a sanitized daily update to GitHub.", text)
        self.assertNotIn("Cycle:", text)
        self.assertNotIn("Status:", text)

    def test_detailed_style_keeps_structured_fields(self) -> None:
        status_payload = {
            "device_id_short": "abcd1234",
            "day": 2,
            "status": "ACTIVE",
            "worker_status": "COMPLETED",
            "cycle_id": "cycle-002-20260301T112400",
            "purpose": "Help clean local beaches by reducing litter hotspots.",
            "becoming": "Improve hotspot detection and daily clean-up guidance.",
        }
        with mock.patch.dict(os.environ, {"WDIB_SLACK_MESSAGE_STYLE": "detailed"}, clear=False):
            text = _build_cycle_text(status_payload, {"pushed": False}, "2026-03-01")

        self.assertIn("WDIB Daily Summary", text)
        self.assertIn("Cycle:", text)
        self.assertIn("Status:", text)


if __name__ == "__main__":
    unittest.main()
