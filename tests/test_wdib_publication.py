#!/usr/bin/env python3
"""Tests for WDIB public publication artifacts."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wdib.publication import build_public_daily_summary, build_public_status  # noqa: E402


class PublicationTests(unittest.TestCase):
    def test_build_public_status_counts(self) -> None:
        now = datetime(2026, 3, 1, 9, 0, 0)
        state = {
            "awoke_on": "2026-02-24",
            "status": "ACTIVE",
            "purpose": {"becoming": "Observe and understand my environment."},
            "tasks": [
                {"status": "IN_PROGRESS", "title": "Map beach litter hotspots"},
                {"status": "TODO", "title": "Improve confidence scoring"},
                {"status": "DONE", "title": "Collect baseline observations"},
            ],
            "hardware_requests": [{"status": "OPEN"}, {"status": "VERIFIED"}],
            "incidents": [{"status": "OPEN"}, {"status": "RESOLVED"}],
        }
        payload = build_public_status(
            device_id="11111111-2222-4333-8444-555555555555",
            cycle_id="cycle-007-20260301T090000",
            day=7,
            state=state,
            worker_status="COMPLETED",
            spirit_text=(
                "## Mission\n"
                "You are determined to help clean up the beach of small-scale human rubbish.\n"
            ),
            summary_hint="Compiled daily hotspot ranking for beach litter observations.",
            now=now,
        )

        self.assertEqual(payload["device_id_short"], "11111111")
        self.assertEqual(payload["first_awoke_on"], "2026-02-24")
        self.assertEqual(payload["counts"]["tasks"]["todo"], 1)
        self.assertEqual(payload["counts"]["tasks"]["in_progress"], 1)
        self.assertEqual(payload["counts"]["tasks"]["done"], 1)
        self.assertEqual(payload["counts"]["hardware_requests"]["open"], 1)
        self.assertEqual(payload["counts"]["hardware_requests"]["verified"], 1)
        self.assertEqual(payload["counts"]["incidents_open"], 1)
        self.assertIn("help clean up the beach", payload["purpose"])
        self.assertIn("hotspot ranking", payload["recent_activity"])
        self.assertEqual(
            payload["next_tasks"],
            ["Map beach litter hotspots", "Improve confidence scoring"],
        )

    def test_daily_summary_redacts_paths_and_skips_technical_reflection(self) -> None:
        now = datetime(2026, 3, 1, 9, 0, 0)
        status_payload = {
            "device_id_short": "abcd1234",
            "cycle_id": "cycle-007-20260301T090000",
            "day": 7,
            "status": "ACTIVE",
            "worker_status": "COMPLETED",
            "becoming": "Understand my local environment.",
            "counts": {
                "tasks": {"todo": 1, "in_progress": 0, "done": 2, "blocked": 0},
                "hardware_requests": {"open": 1, "detected": 0, "verified": 0, "failed": 0},
                "incidents_open": 0,
            },
        }
        markdown = build_public_daily_summary(
            status_payload=status_payload,
            objective="Inspect /devices/abcd1234/state.json and rotate token ABCD1234EFGH5678",
            summary_hint=(
                "Root-cause analysis from `/devices/abcd1234/state.json` and events.ndjson "
                "shows codex runtime failures."
            ),
            now=now,
        )

        self.assertIn("[redacted-path]", markdown)
        self.assertNotIn("state.json", markdown)
        self.assertNotIn("ABCD1234EFGH5678", markdown)
        self.assertNotIn("## Reflection", markdown)


if __name__ == "__main__":
    unittest.main()
