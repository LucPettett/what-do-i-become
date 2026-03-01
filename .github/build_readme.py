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


def _table_cell(value: Any, *, max_len: int = 120) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "..."
    return text.replace("|", "\\|")


def _detail_cell(*, purpose: str, becoming: str, last_activity: str = "", ended: str = "") -> str:
    parts = [
        f"**Purpose:** {purpose}",
        f"**Becoming:** {becoming}",
    ]
    if ended:
        parts.append(f"**Ended:** {ended}")
    else:
        parts.append(f"**Last Activity:** {last_activity}")
    return "<br>".join(parts)


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
        date = str(payload.get("date") or "-").strip() or "-"
        day = payload.get("day")
        try:
            day_int = int(day)
        except (TypeError, ValueError):
            day_int = 0

        becoming = str(payload.get("becoming") or "").strip() or "-"
        purpose = str(payload.get("purpose") or "").strip() or "-"
        recent_activity = str(payload.get("recent_activity") or "").strip() or "-"
        status = str(payload.get("status") or "-").strip().upper() or "-"

        rows.append(
            {
                "device": _table_cell(short_id),
                "awoke": _table_cell(awoke),
                "date": _table_cell(date),
                "day": _table_cell(str(day_int)),
                "day_int": day_int,
                "purpose": _table_cell(purpose, max_len=110),
                "becoming": _table_cell(becoming),
                "recent_activity": _table_cell(recent_activity, max_len=110),
                "status": _table_cell(status),
            }
        )

    rows.sort(key=lambda row: (-int(row["day_int"]), row["device"]))
    return rows


def render_dashboard(rows: list[dict[str, Any]]) -> str:
    active_rows = [row for row in rows if row["status"] != "TERMINATED"]
    terminated_rows = [row for row in rows if row["status"] == "TERMINATED"]

    lines = [
        START_MARKER,
        "Auto-generated from `devices/*/public/status.json`",
        "",
        "---",
        "",
        "## 🟢 Active",
        "",
        "| Device | Day | Details |",
        "|--------|-----|---------|",
    ]

    if not active_rows:
        lines.append("| - | 0 | - |")
    else:
        for row in active_rows:
            detail = _detail_cell(
                purpose=row["purpose"],
                becoming=row["becoming"],
                last_activity=row["recent_activity"],
            )
            lines.append(
                f"| `{row['device']}` | {row['day']} | {detail} |"
            )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 🔴 Terminated",
            "",
            "| Device | Day | Details |",
            "|--------|-----|---------|",
        ]
    )

    if not terminated_rows:
        lines.append("| - | 0 | - |")
    else:
        for row in terminated_rows:
            detail = _detail_cell(
                purpose=row["purpose"],
                becoming=row["becoming"],
                ended=row["date"],
            )
            lines.append(
                f"| `{row['device']}` | {row['day']} | {detail} |"
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
