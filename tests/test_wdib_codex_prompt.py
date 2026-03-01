#!/usr/bin/env python3
"""Tests for WDIB codex worker prompt composition."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wdib.adapters.codex_cli import _build_codex_exec_command, _prompt_from_work_order  # noqa: E402


class CodexPromptTests(unittest.TestCase):
    def _work_order(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "cycle_id": "cycle-001",
            "device_id": "11111111-2222-4333-8444-555555555555",
            "objective": "Fix flaky parser task",
            "allowed_paths": ["/repo/src", "/repo/tests"],
            "result_path": "/repo/devices/x/runtime/worker_results/cycle-001.json",
        }

    def test_prompt_includes_engineering_discipline_requirements(self) -> None:
        prompt = _prompt_from_work_order(self._work_order())

        self.assertIn("find root cause before proposing fixes", prompt)
        self.assertIn("write or update tests first", prompt)
        self.assertIn("run concrete verification commands and report evidence", prompt)
        self.assertIn("Include verification evidence in worker_result.summary.", prompt)
        self.assertIn("make it human/environment-outcome oriented", prompt)
        self.assertIn("Do not use framework-internal becoming statements", prompt)
        self.assertIn("WORK_ORDER_JSON:", prompt)
        self.assertIn('"objective": "Fix flaky parser task"', prompt)

    def test_prompt_disables_web_search_by_default(self) -> None:
        prompt = _prompt_from_work_order(self._work_order())
        self.assertIn("Web search is disabled for this run.", prompt)
        self.assertNotIn("Web search is enabled for this run.", prompt)

    def test_prompt_enables_web_search_when_requested(self) -> None:
        prompt = _prompt_from_work_order(self._work_order(), web_search_enabled=True)
        self.assertIn("Web search is enabled for this run.", prompt)
        self.assertIn("include source URLs in worker_result.summary", prompt)
        self.assertNotIn("Web search is disabled for this run.", prompt)

    def test_build_command_omits_search_flag_when_disabled(self) -> None:
        command = _build_codex_exec_command(
            codex_bin="codex",
            sandbox_mode="workspace-write",
            result_path=Path("/tmp/result.json"),
            project_root=Path("/repo"),
            codex_model="",
            prompt="prompt",
            web_search_enabled=False,
        )
        self.assertNotIn("--search", command)

    def test_build_command_includes_search_flag_when_enabled(self) -> None:
        command = _build_codex_exec_command(
            codex_bin="codex",
            sandbox_mode="workspace-write",
            result_path=Path("/tmp/result.json"),
            project_root=Path("/repo"),
            codex_model="",
            prompt="prompt",
            web_search_enabled=True,
        )
        self.assertIn("--search", command)


if __name__ == "__main__":
    unittest.main()
