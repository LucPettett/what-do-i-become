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

from wdib.adapters import slack_webhook  # noqa: E402
from wdib.adapters.slack_webhook import (  # noqa: E402
    _build_cycle_text,
    _cycle_icon_emoji,
    _normalize_for_slack_mrkdwn,
)


class SlackWebhookFormattingTests(unittest.TestCase):
    def _status_payload(self) -> dict[str, object]:
        return {
            "device_id_short": "abcd1234",
            "day": 2,
            "status": "ACTIVE",
            "worker_status": "COMPLETED",
            "cycle_id": "cycle-002-20260301T112400",
            "purpose": "Help clean local beaches by reducing litter hotspots.",
            "becoming": "Improve hotspot detection and daily clean-up guidance.",
            "recent_activity": "Inspected local shoreline signals and drafted next tasks.",
            "completed_tasks": ["Collect baseline observations"],
            "engineering_details": [
                "`python3 --version` -> Python 3.13.5",
                "`pytest -q` -> 12 passed",
            ],
            "next_tasks": [
                "Improve hotspot detection confidence.",
                "Refine daily clean-up recommendation wording.",
            ],
            "counts": {
                "tasks": {"todo": 2, "in_progress": 1, "done": 1, "blocked": 0},
                "hardware_requests": {"open": 0, "detected": 0, "verified": 0, "failed": 0},
                "incidents_open": 0,
            },
        }

    def test_human_update_message_is_default(self) -> None:
        status_payload = self._status_payload()
        with mock.patch.object(slack_webhook, "_build_cycle_text_llm", return_value=None):
            with mock.patch.dict(os.environ, {}, clear=False):
                text = _build_cycle_text(status_payload, {"pushed": True}, "2026-03-01")

        self.assertIn("journal, cycle", text)
        self.assertIn(":coffee:", text)
        self.assertIn("*What I did*", text)
        self.assertIn("Completed: Collect baseline observations", text)
        self.assertIn("*What I'm thinking*", text)
        self.assertIn("*Engineering notes*", text)
        self.assertIn("`python3 --version` -> Python 3.13.5", text)
        self.assertIn("*What's next*", text)
        self.assertIn("• Improve hotspot detection confidence.", text)
        self.assertNotIn("Published today's public update", text)
        self.assertNotIn("Tasks moved:", text)
        self.assertNotIn("Cycle:", text)
        self.assertNotIn("Status:", text)
        self.assertNotIn("Privacy:", text)
        self.assertIn("•", text)

    def test_llm_path_prefers_model_text(self) -> None:
        status_payload = self._status_payload()
        with mock.patch.object(
            slack_webhook,
            "_build_cycle_text_llm",
            return_value="*LLM update*\n\nI improved signal quality today.",
        ):
            text = _build_cycle_text(status_payload, {"pushed": True}, "2026-03-01")
        self.assertIn("LLM update", text)
        self.assertNotIn("journal, cycle", text)

    def test_llm_falls_back_to_human_when_unavailable(self) -> None:
        status_payload = self._status_payload()
        with mock.patch.object(slack_webhook, "_build_cycle_text_llm", return_value=None):
            text = _build_cycle_text(status_payload, {"pushed": True}, "2026-03-01")
        self.assertIn("journal, cycle", text)
        self.assertIn(":coffee:", text)

    def test_human_awakening_message_has_awoke_header(self) -> None:
        status_payload = {
            "device_id_short": "abcd1234",
            "day": 1,
            "status": "ACTIVE",
            "worker_status": "COMPLETED",
            "cycle_id": "cycle-001-20260301T112400",
            "purpose": "Help clean local beaches by reducing litter hotspots.",
            "becoming": "Improve hotspot detection and daily clean-up guidance.",
            "system_profile": "wlan0 is online; outbound connectivity checks passed; I2C buses are available.",
            "recent_activity": "Inspected local shoreline signals and drafted next tasks.",
            "engineering_details": ["`ip -brief addr` -> wlan0 UP [redacted-ip]/24"],
            "next_tasks": ["Improve hotspot detection confidence."],
            "counts": {
                "tasks": {"todo": 1, "in_progress": 0, "done": 0, "blocked": 0},
                "hardware_requests": {"open": 0, "detected": 0, "verified": 0, "failed": 0},
                "incidents_open": 0,
            },
        }
        with mock.patch.object(slack_webhook, "_build_cycle_text_llm", return_value=None):
            with mock.patch.dict(os.environ, {}, clear=False):
                text = _build_cycle_text(status_payload, {"pushed": False}, "2026-03-01")

        self.assertIn("I awoke and", text)
        self.assertIn(":sunrise:", text)
        self.assertIn("Explored myself.", text)
        self.assertIn("I've reviewed my spirit", text)
        self.assertIn("What's next:", text)
        self.assertIn("• Improve hotspot detection confidence.", text)
        self.assertIn("Engineering details:", text)
        self.assertNotIn("Tasks moved:", text)
        self.assertNotIn("Published:", text)
        self.assertIn("•", text)

    def test_human_terminate_message_is_distinct(self) -> None:
        status_payload = {
            "device_id_short": "abcd1234",
            "day": 4,
            "status": "TERMINATED",
            "worker_status": "TERMINATED",
            "cycle_id": "cycle-004-20260301T112400",
            "purpose": "Help clean local beaches by reducing litter hotspots.",
            "becoming": "Gracefully conclude this mission run and hand over cleanly.",
            "recent_activity": "Received human termination instruction and gracefully ended this run.",
            "self_observation": "I received a human termination command and gracefully closed this chapter.",
            "completed_tasks": ["Implemented local weather feed ingestion", "Shipped first daily briefing template"],
            "engineering_details": [
                "`python3 -m unittest` -> 21 tests passed",
                "`ip -brief addr` -> wlan0 UP [redacted-ip]/24",
            ],
            "counts": {
                "tasks": {"todo": 0, "in_progress": 0, "done": 2, "blocked": 0},
                "hardware_requests": {"open": 0, "detected": 0, "verified": 0, "failed": 0},
                "incidents_open": 0,
            },
        }
        with mock.patch.object(slack_webhook, "_build_cycle_text_llm", return_value=None):
            with mock.patch.dict(os.environ, {}, clear=False):
                text = _build_cycle_text(status_payload, {"pushed": True}, "2026-03-01")

        self.assertIn("Closing journal - ✌️", text)
        self.assertIn("I've been told to terminate", text)
        self.assertIn("Final thoughts:", text)
        self.assertIn("We completed:", text)
        self.assertIn("Engineering highlights:", text)
        self.assertIn("I'm terminating now. Goodbye.", text)
        self.assertNotIn("•", text)

    def test_icon_emoji_defaults_by_cycle_phase(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            self.assertEqual(_cycle_icon_emoji({"day": 1}), ":sunrise:")
            self.assertEqual(_cycle_icon_emoji({"day": 2}), ":coffee:")
            self.assertEqual(_cycle_icon_emoji({"day": 3, "status": "TERMINATED"}), "")

    def test_icon_emoji_can_be_overridden_by_env(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "WDIB_SLACK_AWAKENING_EMOJI": ":sunrise:",
                "WDIB_SLACK_UPDATE_EMOJI": ":coffee:",
            },
            clear=False,
        ):
            self.assertEqual(_cycle_icon_emoji({"day": 1}), ":sunrise:")
            self.assertEqual(_cycle_icon_emoji({"day": 3}), ":coffee:")

    def test_normalize_for_slack_mrkdwn_converts_double_asterisk_bold(self) -> None:
        raw = "**What I did**\n- Ran __checks__\n- kept *existing* slack bold"
        normalized = _normalize_for_slack_mrkdwn(raw)
        self.assertIn("*What I did*", normalized)
        self.assertIn("*checks*", normalized)
        self.assertIn("*existing*", normalized)
        self.assertNotIn("**What I did**", normalized)
        self.assertNotIn("__checks__", normalized)


if __name__ == "__main__":
    unittest.main()
