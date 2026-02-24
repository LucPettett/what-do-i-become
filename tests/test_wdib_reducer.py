#!/usr/bin/env python3
"""Tests for WDIB reducer semantics."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wdib.control.reducer import apply_worker_result  # noqa: E402


class ReducerTests(unittest.TestCase):
    def test_proposed_hardware_request_blocks_system_until_verified(self) -> None:
        state = {
            "schema_version": "1.0",
            "device_id": "11111111-2222-4333-8444-555555555555",
            "awoke_on": "2026-02-24",
            "day": 1,
            "purpose": {"becoming": "", "spirit_path": "src/SPIRIT.md"},
            "status": "ACTIVE",
            "tasks": [],
            "hardware_requests": [],
            "incidents": [],
            "artifacts": [],
            "last_summary": "",
        }

        worker_result = {
            "schema_version": "1.0",
            "cycle_id": "cycle-001",
            "status": "COMPLETED",
            "summary": "Need camera to proceed",
            "proposed_hardware_requests": [
                {
                    "name": "USB Camera",
                    "reason": "Need visual input",
                    "detection": {"kind": "glob_exists", "value": "/dev/video*"},
                    "verify_command": "v4l2-ctl --all",
                }
            ],
        }

        events = apply_worker_result(state, worker_result)

        self.assertEqual(state["status"], "BLOCKED_HARDWARE")
        self.assertEqual(len(state["hardware_requests"]), 1)
        request = state["hardware_requests"][0]
        self.assertEqual(request["status"], "OPEN")
        self.assertEqual(request["name"], "USB Camera")
        self.assertEqual(request["detection"]["kind"], "glob_exists")
        self.assertEqual(request["verify_command"], "v4l2-ctl --all")
        self.assertEqual(state["last_summary"], "Need camera to proceed")
        self.assertEqual(events[0]["type"], "HARDWARE_REQUEST_CREATED")

    def test_failed_worker_result_sets_error_and_creates_incident(self) -> None:
        state = {
            "schema_version": "1.0",
            "device_id": "11111111-2222-4333-8444-555555555555",
            "awoke_on": "2026-02-24",
            "day": 1,
            "purpose": {"becoming": "", "spirit_path": "src/SPIRIT.md"},
            "status": "ACTIVE",
            "tasks": [],
            "hardware_requests": [],
            "incidents": [],
            "artifacts": [],
            "last_summary": "",
        }

        worker_result = {
            "schema_version": "1.0",
            "cycle_id": "cycle-002",
            "status": "FAILED",
            "summary": "Build failed after repeated retries",
        }

        apply_worker_result(state, worker_result)

        self.assertEqual(state["status"], "ERROR")
        self.assertEqual(len(state["incidents"]), 1)
        incident = state["incidents"][0]
        self.assertEqual(incident["title"], "Worker execution failed")
        self.assertEqual(incident["severity"], "HIGH")


if __name__ == "__main__":
    unittest.main()
