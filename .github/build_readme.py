#!/usr/bin/env python3
"""Build README dashboard from devices/*/public/status.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
DEVICES_DIR = ROOT / "devices"

START_MARKER = "<!-- DEVICE_DASHBOARD_START -->"
END_MARKER = "<!-- DEVICE_DASHBOARD_END -->"


def _table_cell(value: Any) -> str:
    text = str(value or "").replace("\n", " ").strip()
    return text.replace("|", "\\|")


def load_device_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not DEVICES_DIR.exists():
        return rows

    for status_json in sorted(DEVICES_DIR.glob("*/public/status.json")):
        try:
            payload = json.loads(status_json.read_text(encoding="utf-8")) or {}
        except Exception:
            continue

        short_id = str(payload.get("device_id_short") or status_json.parent.parent.name[:8]).strip() or "-"
        awoke = str(payload.get("first_awoke_on") or payload.get("date") or "-").strip() or "-"
        day = payload.get("day")
        try:
            day_display = str(int(day))
        except (TypeError, ValueError):
            day_display = "0"

        becoming = str(payload.get("becoming") or "").strip() or "-"
        status = str(payload.get("status") or "-").strip() or "-"

        rows.append(
            {
                "device": _table_cell(short_id),
                "awoke": _table_cell(awoke),
                "day": _table_cell(day_display),
                "becoming": _table_cell(becoming),
                "status": _table_cell(status),
            }
        )

    rows.sort(key=lambda row: (row["awoke"], row["device"]))
    return rows


def render_dashboard(rows: list[dict[str, Any]]) -> str:
    lines = [
        START_MARKER,
        "| Device | Awoke | Day | Becoming | Status |",
        "| --- | --- | ---: | --- | --- |",
    ]

    if not rows:
        lines.append("| - | - | 0 | - | - |")
    else:
        for row in rows:
            lines.append(
                f"| `{row['device']}` | {row['awoke']} | {row['day']} | {row['becoming']} | {row['status']} |"
            )

    lines.append(END_MARKER)
    return "\n".join(lines)


def replace_dashboard(readme_text: str, dashboard_text: str) -> str:
    if START_MARKER in readme_text and END_MARKER in readme_text:
        start_idx = readme_text.index(START_MARKER)
        end_idx = readme_text.index(END_MARKER) + len(END_MARKER)
        return readme_text[:start_idx] + dashboard_text + readme_text[end_idx:]

    suffix = (
        "\n\n## Device Dashboard\n"
        "Auto-generated from `devices/*/public/status.json`.\n\n"
        f"{dashboard_text}\n"
    )
    return readme_text.rstrip() + suffix


def main() -> None:
    rows = load_device_rows()
    dashboard = render_dashboard(rows)

    if README_PATH.exists():
        current = README_PATH.read_text(encoding="utf-8")
    else:
        current = "# what-do-i-become\n"

    updated = replace_dashboard(current, dashboard)

    if updated != current:
        README_PATH.write_text(updated, encoding="utf-8")
        print("README dashboard updated")
    else:
        print("README dashboard unchanged")


if __name__ == "__main__":
    main()
