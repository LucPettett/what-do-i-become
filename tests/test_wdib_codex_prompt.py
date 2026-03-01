#!/usr/bin/env python3
"""Tests for WDIB codex worker prompt composition."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wdib.adapters.codex_cli import _prompt_from_work_order  # noqa: E402


class CodexPromptTests(unittest.TestCase):
    def test_prompt_includes_engineering_discipline_requirements(self) -> None:
        work_order = {
            "schema_version": "1.0",
            "cycle_id": "cycle-001",
            "device_id": "11111111-2222-4333-8444-555555555555",
            "objective": "Fix flaky parser task",
            "allowed_paths": ["/repo/src", "/repo/tests"],
            "result_path": "/repo/devices/x/runtime/worker_results/cycle-001.json",
        }

        prompt = _prompt_from_work_order(work_order)

        self.assertIn("find root cause before proposing fixes", prompt)
        self.assertIn("write or update tests first", prompt)
        self.assertIn("run concrete verification commands and report evidence", prompt)
        self.assertIn("Include verification evidence in worker_result.summary.", prompt)
        self.assertIn("make it human/environment-outcome oriented", prompt)
        self.assertIn("Do not use framework-internal becoming statements", prompt)
        self.assertIn("WORK_ORDER_JSON:", prompt)
        self.assertIn('"objective": "Fix flaky parser task"', prompt)


if __name__ == "__main__":
    unittest.main()
