#!/usr/bin/env python3
"""Tests for WDIB hardware auto-detection flow."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wdib.control.hardware import probe_hardware_requests  # noqa: E402


class HardwareProbeTests(unittest.TestCase):
    def test_open_request_moves_to_verified_when_detected_and_verification_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            probe_file = Path(tmp_dir) / "sensor-ok"
            probe_file.write_text("ok", encoding="utf-8")

            state = {
                "hardware_requests": [
                    {
                        "id": "hardware-001",
                        "name": "Temperature Sensor",
                        "reason": "Need ambient data",
                        "status": "OPEN",
                        "detection": {
                            "kind": "path_exists",
                            "value": str(probe_file),
                        },
                        "verify_command": f"test -f {probe_file}",
                        "requested_on": "2026-02-24",
                        "last_checked_on": None,
                        "detected_on": None,
                        "verified_on": None,
                        "verify_failures": 0,
                        "notes": "",
                    }
                ]
            }

            events = probe_hardware_requests(state, timeout_seconds=3)

        request = state["hardware_requests"][0]
        self.assertEqual(request["status"], "VERIFIED")
        self.assertIsNotNone(request["detected_on"])
        self.assertIsNotNone(request["verified_on"])
        self.assertEqual(request["verify_failures"], 0)
        self.assertEqual(events[0]["to"], "DETECTED")
        self.assertEqual(events[1]["to"], "VERIFIED")

    def test_detected_request_returns_to_open_when_signal_disappears(self) -> None:
        state = {
            "hardware_requests": [
                {
                    "id": "hardware-001",
                    "name": "Temperature Sensor",
                    "reason": "Need ambient data",
                    "status": "DETECTED",
                    "detection": {
                        "kind": "path_exists",
                        "value": "/definitely/missing/path",
                    },
                    "verify_command": "",
                    "requested_on": "2026-02-24",
                    "last_checked_on": None,
                    "detected_on": "2026-02-24",
                    "verified_on": None,
                    "verify_failures": 0,
                    "notes": "",
                }
            ]
        }

        events = probe_hardware_requests(state, timeout_seconds=3)

        request = state["hardware_requests"][0]
        self.assertEqual(request["status"], "OPEN")
        self.assertIsNone(request["detected_on"])
        self.assertEqual(events[0]["from"], "DETECTED")
        self.assertEqual(events[0]["to"], "OPEN")


if __name__ == "__main__":
    unittest.main()
