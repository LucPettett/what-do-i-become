"""Pre-departure power readiness helpers and CLI."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


class PowerReadinessError(ValueError):
    """Raised when power readiness cannot be collected or interpreted."""


_PERCENT_RE = re.compile(r"(\d+)%")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s+remaining")


def parse_pmset_batt_output(raw_output: str) -> dict[str, Any]:
    """Parse `pmset -g batt` output into a normalized snapshot."""
    text = str(raw_output or "").strip()
    if not text:
        raise PowerReadinessError("Empty pmset output.")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise PowerReadinessError("pmset output contained no parseable lines.")

    power_source = "unknown"
    source_line = lines[0]
    source_match = re.search(r"Now drawing from '([^']+)'", source_line)
    if source_match:
        power_source = source_match.group(1).strip()

    status_line = ""
    for line in lines[1:]:
        if "%" in line and ";" in line:
            status_line = line
            break
    if not status_line:
        for line in lines:
            if "%" in line and ";" in line:
                status_line = line
                break
    if not status_line:
        raise PowerReadinessError("Unable to find battery status line in pmset output.")

    parts = [part.strip() for part in status_line.split(";")]
    percent_match = _PERCENT_RE.search(parts[0] if parts else status_line)
    if not percent_match:
        raise PowerReadinessError("Unable to parse battery percentage from pmset output.")

    battery_percent = int(percent_match.group(1))
    charge_state = "unknown"
    if len(parts) >= 2:
        charge_state = str(parts[1]).strip().lower() or "unknown"

    time_remaining_min = None
    time_match = _TIME_RE.search(status_line)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        time_remaining_min = hours * 60 + minutes

    return {
        "power_source": power_source,
        "battery_percent": battery_percent,
        "charge_state": charge_state,
        "time_remaining_min": time_remaining_min,
        "raw_source_line": source_line,
        "raw_status_line": status_line,
    }


def collect_power_snapshot(*, pmset_output: str | None = None) -> dict[str, Any]:
    """Collect and parse battery status from either provided text or `pmset`."""
    if pmset_output is None:
        try:
            proc = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
        except Exception as exc:
            raise PowerReadinessError(f"Failed to execute `pmset -g batt`: {exc}") from exc

        output = (proc.stdout or "").strip()
        if proc.returncode != 0 or not output:
            stderr = (proc.stderr or "").strip()
            raise PowerReadinessError(
                f"`pmset -g batt` failed (code={proc.returncode}): {stderr or 'no output'}"
            )
    else:
        output = str(pmset_output)

    return parse_pmset_batt_output(output)


def _build_action_tips(
    *,
    battery_percent: int,
    charge_state: str,
    power_source: str,
    min_departure_percent: int,
) -> list[str]:
    tips: list[str] = []

    if battery_percent < min_departure_percent:
        tips.append(f"Pause departure until battery reaches at least {min_departure_percent}%.")
        tips.append("Connect a high-watt charger and confirm the charging indicator within 60 seconds.")

    if power_source == "AC Power" and charge_state == "discharging":
        tips.append("Reseat the charger cable and adapter, then retry a different outlet.")

    if charge_state == "discharging":
        tips.append("Reduce high-drain tasks before departure and keep a charged power bank ready.")

    if battery_percent >= min_departure_percent and charge_state in {"charging", "charged"}:
        tips.append("Maintain charging until departure to preserve a buffer for unexpected delays.")

    fallback = [
        "Run a final battery check within 5 minutes of leaving.",
        "Pack the known-good charger in your bag.",
        "If charge behavior is unstable, delay non-urgent travel until stable charging resumes.",
    ]
    for tip in fallback:
        if len(tips) >= 3:
            break
        if tip not in tips:
            tips.append(tip)

    return tips[:3]


def evaluate_power_readiness(
    snapshot: dict[str, Any],
    *,
    min_departure_percent: int = 40,
) -> dict[str, Any]:
    """Classify pre-departure power readiness and return actionable guidance."""
    if not isinstance(min_departure_percent, int) or min_departure_percent <= 0 or min_departure_percent > 100:
        raise PowerReadinessError("min_departure_percent must be an integer between 1 and 100.")

    battery_percent = int(snapshot.get("battery_percent"))
    charge_state = str(snapshot.get("charge_state") or "unknown").strip().lower()
    power_source = str(snapshot.get("power_source") or "unknown").strip()

    reasons: list[str] = []
    risk_rank = 1

    if battery_percent < 20:
        risk_rank = max(risk_rank, 3)
        reasons.append("Battery is below 20%, which creates immediate run-out risk.")
    elif battery_percent < min_departure_percent:
        risk_rank = max(risk_rank, 2)
        reasons.append(
            f"Battery is below the departure threshold ({battery_percent}% < {min_departure_percent}%)."
        )

    if charge_state == "discharging" and battery_percent < min_departure_percent:
        risk_rank = max(risk_rank, 3)
        reasons.append("Battery is discharging below departure threshold.")

    if power_source == "AC Power" and charge_state == "discharging":
        risk_rank = max(risk_rank, 3)
        reasons.append("AC Power is connected but battery is still discharging.")

    if not reasons:
        reasons.append("Battery and charging state meet departure threshold.")

    risk_level = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}[risk_rank]
    ready = risk_level == "LOW"
    action_tips = _build_action_tips(
        battery_percent=battery_percent,
        charge_state=charge_state,
        power_source=power_source,
        min_departure_percent=min_departure_percent,
    )

    return {
        "ready": ready,
        "risk_level": risk_level,
        "min_departure_percent": min_departure_percent,
        "reasons": reasons,
        "action_tips": action_tips,
    }


def append_power_readiness_record(
    *,
    log_path: Path,
    now: datetime,
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    notes: str,
) -> dict[str, Any]:
    """Append one pre-departure power readiness record to NDJSON log."""
    record = {
        "ts": now.isoformat(),
        "power_source": snapshot.get("power_source"),
        "battery_percent": snapshot.get("battery_percent"),
        "charge_state": snapshot.get("charge_state"),
        "time_remaining_min": snapshot.get("time_remaining_min"),
        "assessment": assessment,
        "notes": str(notes or "").strip(),
    }

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    return record


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="power_readiness")
    parser.add_argument("--log-path", required=True, help="Path to NDJSON power readiness log.")
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Report readiness without appending a log record.",
    )
    parser.add_argument(
        "--min-departure-percent",
        type=int,
        default=40,
        help="Battery percent threshold required to treat departure as ready.",
    )
    parser.add_argument("--notes", default="", help="Optional operator notes for appended records.")
    parser.add_argument(
        "--pmset-output-path",
        default="",
        help="Optional text file containing pmset output for deterministic runs/tests.",
    )
    parser.add_argument(
        "--now",
        default="",
        help="ISO timestamp override for deterministic runs (defaults to local now).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    now = datetime.now().astimezone()
    if args.now:
        now = datetime.fromisoformat(args.now)
        if now.tzinfo is None:
            now = now.astimezone()

    pmset_output = None
    if args.pmset_output_path:
        pmset_output = Path(args.pmset_output_path).read_text(encoding="utf-8")

    try:
        snapshot = collect_power_snapshot(pmset_output=pmset_output)
        assessment = evaluate_power_readiness(
            snapshot,
            min_departure_percent=args.min_departure_percent,
        )
    except (PowerReadinessError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1

    if args.status_only:
        print(json.dumps({"ok": True, "snapshot": snapshot, "assessment": assessment}, sort_keys=True))
        return 0

    log_path = Path(args.log_path)
    record = append_power_readiness_record(
        log_path=log_path,
        now=now,
        snapshot=snapshot,
        assessment=assessment,
        notes=args.notes,
    )
    print(json.dumps({"ok": True, "record": record}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
