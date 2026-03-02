#!/usr/bin/env python3
"""Tests for pre-departure power readiness logic."""

from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wdib.control.power_readiness import (  # noqa: E402
    evaluate_power_readiness,
    main,
    parse_pmset_batt_output,
)


SAMPLE_PMSET_AC_DISCHARGING = """Now drawing from 'AC Power'
 -InternalBattery-0 (id=1234567)\t25%; discharging; 3:06 remaining present: true
"""

SAMPLE_PMSET_BATTERY_DISCHARGING = """Now drawing from 'Battery Power'
 -InternalBattery-0 (id=1234567)\t19%; discharging; 1:03 remaining present: true
"""

SAMPLE_PMSET_CHARGING = """Now drawing from 'AC Power'
 -InternalBattery-0 (id=1234567)\t72%; charging; 0:54 remaining present: true
"""


class PowerReadinessTests(unittest.TestCase):
    def test_parse_pmset_batt_output_extracts_core_fields(self) -> None:
        snapshot = parse_pmset_batt_output(SAMPLE_PMSET_AC_DISCHARGING)

        self.assertEqual(snapshot["power_source"], "AC Power")
        self.assertEqual(snapshot["battery_percent"], 25)
        self.assertEqual(snapshot["charge_state"], "discharging")
        self.assertEqual(snapshot["time_remaining_min"], 186)

    def test_evaluate_power_readiness_high_risk_on_low_battery(self) -> None:
        snapshot = parse_pmset_batt_output(SAMPLE_PMSET_BATTERY_DISCHARGING)

        assessment = evaluate_power_readiness(snapshot, min_departure_percent=40)

        self.assertEqual(assessment["risk_level"], "HIGH")
        self.assertFalse(assessment["ready"])
        self.assertEqual(len(assessment["action_tips"]), 3)
        self.assertIn("Pause departure until battery reaches at least 40%.", assessment["action_tips"])

    def test_evaluate_power_readiness_flags_ac_discharging_anomaly(self) -> None:
        snapshot = parse_pmset_batt_output(SAMPLE_PMSET_AC_DISCHARGING)

        assessment = evaluate_power_readiness(snapshot, min_departure_percent=40)

        self.assertEqual(assessment["risk_level"], "HIGH")
        self.assertFalse(assessment["ready"])
        self.assertIn("AC Power is connected but battery is still discharging.", assessment["reasons"])

    def test_cli_status_only_reports_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "power_readiness_2026-03-01.ndjson"
            pmset_path = Path(tmp_dir) / "pmset.txt"
            pmset_path.write_text(SAMPLE_PMSET_CHARGING, encoding="utf-8")

            captured = StringIO()
            with redirect_stdout(captured):
                rc = main(
                    [
                        "--log-path",
                        str(log_path),
                        "--status-only",
                        "--pmset-output-path",
                        str(pmset_path),
                        "--now",
                        "2026-03-01T07:15:00+10:00",
                    ]
                )

            self.assertEqual(rc, 0)
            payload = json.loads(captured.getvalue().strip())
            self.assertTrue(payload["ok"])
            self.assertIn("snapshot", payload)
            self.assertIn("assessment", payload)
            self.assertFalse(log_path.exists())

    def test_cli_appends_record_when_not_status_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "power_readiness_2026-03-01.ndjson"
            pmset_path = Path(tmp_dir) / "pmset.txt"
            pmset_path.write_text(SAMPLE_PMSET_CHARGING, encoding="utf-8")

            captured = StringIO()
            with redirect_stdout(captured):
                rc = main(
                    [
                        "--log-path",
                        str(log_path),
                        "--pmset-output-path",
                        str(pmset_path),
                        "--now",
                        "2026-03-01T07:15:00+10:00",
                        "--notes",
                        "Morning pre-departure check",
                    ]
                )

            self.assertEqual(rc, 0)
            payload = json.loads(captured.getvalue().strip())
            self.assertTrue(payload["ok"])
            self.assertIn("record", payload)

            rows = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["battery_percent"], 72)
            self.assertEqual(row["assessment"]["risk_level"], "LOW")
            self.assertEqual(row["notes"], "Morning pre-departure check")
            self.assertEqual(
                datetime.fromisoformat(row["ts"]).date().isoformat(),
                "2026-03-01",
            )


if __name__ == "__main__":
    unittest.main()
