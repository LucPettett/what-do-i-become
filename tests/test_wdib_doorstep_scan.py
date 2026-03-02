#!/usr/bin/env python3
"""Tests for doorstep hazard scan logic."""

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

from wdib.control.doorstep_scan import (  # noqa: E402
    DuplicateSlotError,
    WindowError,
    append_scan_record,
    cadence_status,
    choose_slot,
    generate_action_tips,
    main,
)


class DoorstepScanTests(unittest.TestCase):
    def test_choose_slot_respects_windows(self) -> None:
        morning = datetime.fromisoformat("2026-03-01T07:15:00+10:00")
        evening = datetime.fromisoformat("2026-03-01T18:30:00+10:00")
        midday = datetime.fromisoformat("2026-03-01T14:15:00+10:00")

        self.assertEqual(choose_slot(morning, "auto"), "morning")
        self.assertEqual(choose_slot(evening, "auto"), "evening")
        with self.assertRaises(WindowError):
            choose_slot(midday, "auto")

    def test_generate_action_tips_produces_exactly_three(self) -> None:
        tips = generate_action_tips(
            precipitation="moderate",
            wind="strong",
            visibility="clear",
            surface="wet",
        )

        self.assertEqual(len(tips), 3)
        self.assertIn("Carry an umbrella and wear a water-resistant outer layer.", tips)
        self.assertIn("Secure outerwear and avoid exposed route segments.", tips)
        self.assertIn("Wear slip-resistant footwear and choose the safer route.", tips)

    def test_generate_action_tips_unknown_conditions_use_fallbacks(self) -> None:
        tips = generate_action_tips(
            precipitation="unknown",
            wind="unknown",
            visibility="unknown",
            surface="unknown",
        )

        self.assertEqual(len(tips), 3)
        self.assertEqual(
            tips[0],
            "Run a 2-minute physical doorway check immediately before departure.",
        )

    def test_append_scan_record_rejects_duplicate_slot_same_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "scan_log_2026-03-01.ndjson"

            first = append_scan_record(
                log_path=log_path,
                now=datetime.fromisoformat("2026-03-01T07:20:00+10:00"),
                slot="morning",
                precipitation="none",
                wind="calm",
                visibility="clear",
                surface="dry",
                confidence="observed",
                notes="Initial check",
            )

            self.assertEqual(first["slot"], "morning")

            with self.assertRaises(DuplicateSlotError):
                append_scan_record(
                    log_path=log_path,
                    now=datetime.fromisoformat("2026-03-01T08:30:00+10:00"),
                    slot="morning",
                    precipitation="none",
                    wind="calm",
                    visibility="clear",
                    surface="dry",
                    confidence="observed",
                    notes="Duplicate check",
                )

            rows = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(rows), 1)

    def test_cadence_status_flags_due_overdue_and_next_slot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "scan_log_2026-03-01.ndjson"

            pre_window = cadence_status(
                log_path,
                datetime.fromisoformat("2026-03-01T05:50:00+10:00"),
            )
            self.assertFalse(pre_window["should_scan_now"])
            self.assertEqual(pre_window["next_slot"], "morning")
            self.assertEqual(pre_window["overdue_slots_today"], [])

            morning_window = cadence_status(
                log_path,
                datetime.fromisoformat("2026-03-01T07:10:00+10:00"),
            )
            self.assertTrue(morning_window["should_scan_now"])
            self.assertEqual(morning_window["current_window_slot"], "morning")

            missed_morning = cadence_status(
                log_path,
                datetime.fromisoformat("2026-03-01T10:15:00+10:00"),
            )
            self.assertEqual(missed_morning["overdue_slots_today"], ["morning"])
            self.assertEqual(missed_morning["next_slot"], "evening")

    def test_cadence_status_marks_day_complete_after_both_slots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "scan_log_2026-03-01.ndjson"

            append_scan_record(
                log_path=log_path,
                now=datetime.fromisoformat("2026-03-01T07:20:00+10:00"),
                slot="morning",
                precipitation="none",
                wind="calm",
                visibility="clear",
                surface="dry",
                confidence="observed",
                notes="Morning observed check",
            )
            append_scan_record(
                log_path=log_path,
                now=datetime.fromisoformat("2026-03-01T18:10:00+10:00"),
                slot="evening",
                precipitation="light",
                wind="breezy",
                visibility="clear",
                surface="damp",
                confidence="observed",
                notes="Evening observed check",
            )

            status = cadence_status(
                log_path,
                datetime.fromisoformat("2026-03-01T19:00:00+10:00"),
            )
            self.assertEqual(status["remaining_slots_today"], [])
            self.assertEqual(status["next_slot"], "")
            self.assertFalse(status["should_scan_now"])

    def test_cli_status_only_reports_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "scan_log_2026-03-01.ndjson"

            captured = StringIO()
            with redirect_stdout(captured):
                rc = main(
                    [
                        "--log-path",
                        str(log_path),
                        "--status-only",
                        "--now",
                        "2026-03-01T07:05:00+10:00",
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(captured.getvalue().strip())
            self.assertTrue(payload["ok"])
            self.assertIn("status", payload)
            self.assertFalse(log_path.exists())


if __name__ == "__main__":
    unittest.main()
