#!/usr/bin/env python3
"""Tests for WDIB notification routing."""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wdib.notifications.router import send_cycle_notifications  # noqa: E402


class NotificationRouterTests(unittest.TestCase):
    def test_no_channels_configured_returns_no_results(self) -> None:
        with mock.patch.dict(os.environ, {"WDIB_NOTIFICATION_CHANNELS": ""}, clear=False):
            results = send_cycle_notifications(
                status_payload={"device_id_short": "abcd1234", "day": 1, "status": "ACTIVE"},
                git_info={"pushed": True},
                run_date="2026-03-01",
            )
        self.assertEqual(results, [])

    def test_unknown_and_unconfigured_channels_are_reported(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "WDIB_NOTIFICATION_CHANNELS": "slack,unknown",
                "WDIB_SLACK_WEBHOOK_URL": "",
            },
            clear=False,
        ):
            results = send_cycle_notifications(
                status_payload={"device_id_short": "abcd1234", "day": 1, "status": "ACTIVE"},
                git_info={"pushed": True},
                run_date="2026-03-01",
            )

        by_channel = {str(item.get("channel")): item for item in results}
        self.assertIn("slack", by_channel)
        self.assertIn("unknown", by_channel)
        self.assertFalse(bool(by_channel["slack"].get("sent")))
        self.assertIn("not configured", str(by_channel["slack"].get("reason")))
        self.assertFalse(bool(by_channel["unknown"].get("sent")))
        self.assertIn("not registered", str(by_channel["unknown"].get("reason")))


if __name__ == "__main__":
    unittest.main()
