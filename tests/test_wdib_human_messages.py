#!/usr/bin/env python3
"""Tests for WDIB human message inbox behavior."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wdib.control.human_messages import (  # noqa: E402
    enqueue_human_message,
    is_terminate_command,
    load_and_clear_human_message,
)


class HumanMessageTests(unittest.TestCase):
    def test_enqueue_and_consume_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            with mock.patch.dict(os.environ, {"WDIB_DEVICE_ID": "11111111-2222-4333-8444-555555555555"}, clear=False):
                with mock.patch("wdib.paths.PROJECT_ROOT", project_root):
                    with mock.patch("wdib.paths.DEVICES_DIR", project_root / "devices"):
                        with mock.patch(
                            "wdib.storage.repository.DEVICES_DIR",
                            project_root / "devices",
                        ):
                            path = enqueue_human_message(
                                "11111111-2222-4333-8444-555555555555",
                                "terminate now and say goodbye",
                            )
                            self.assertTrue(path.exists())
                            loaded = load_and_clear_human_message(
                                "11111111-2222-4333-8444-555555555555"
                            )
                            self.assertEqual(loaded, "terminate now and say goodbye")
                            self.assertFalse(path.exists())

    def test_terminate_parser_accepts_common_phrasing(self) -> None:
        self.assertTrue(is_terminate_command("Please terminate this device now."))
        self.assertTrue(is_terminate_command("shutdown and goodbye"))
        self.assertFalse(is_terminate_command("continue with normal work"))


if __name__ == "__main__":
    unittest.main()
