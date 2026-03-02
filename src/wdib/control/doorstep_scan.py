"""Doorstep hazard scan helpers and CLI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, time
from pathlib import Path
from typing import Any


class DoorstepScanError(ValueError):
    """Base error for scan operations."""


class WindowError(DoorstepScanError):
    """Raised when auto slot resolution occurs outside scan windows."""


class DuplicateSlotError(DoorstepScanError):
    """Raised when a morning/evening slot already exists for the same day."""


_VALID_SLOT_INPUTS = {"auto", "morning", "evening", "setup"}
_VALID_PRECIPITATION = {"none", "light", "moderate", "heavy", "unknown"}
_VALID_WIND = {"calm", "breezy", "strong", "unknown"}
_VALID_VISIBILITY = {"clear", "reduced", "poor", "unknown"}
_VALID_SURFACE = {"dry", "damp", "wet", "slippery", "obstructed", "unknown"}
_VALID_CONFIDENCE = {"observed", "inferred", "unknown"}

_MORNING_START = time(6, 30)
_MORNING_END = time(9, 0)
_EVENING_START = time(17, 0)
_EVENING_END = time(20, 0)
_WINDOW_RANGES = {
    "morning": "06:30-09:00",
    "evening": "17:00-20:00",
}


def _validate_choice(name: str, value: str, allowed: set[str]) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in allowed:
        allowed_csv = ", ".join(sorted(allowed))
        raise DoorstepScanError(f"Invalid {name}: {value!r}. Allowed: {allowed_csv}")
    return normalized


def choose_slot(now: datetime, slot: str) -> str:
    slot_value = _validate_choice("slot", slot, _VALID_SLOT_INPUTS)
    if slot_value != "auto":
        return slot_value

    clock = now.timetz().replace(tzinfo=None)
    if _MORNING_START <= clock <= _MORNING_END:
        return "morning"
    if _EVENING_START <= clock <= _EVENING_END:
        return "evening"
    raise WindowError(
        "Auto slot resolution failed because local time is outside "
        "06:30-09:00 and 17:00-20:00 windows."
    )


def generate_action_tips(
    *,
    precipitation: str,
    wind: str,
    visibility: str,
    surface: str,
) -> list[str]:
    precip_value = _validate_choice("precipitation", precipitation, _VALID_PRECIPITATION)
    wind_value = _validate_choice("wind", wind, _VALID_WIND)
    visibility_value = _validate_choice("visibility", visibility, _VALID_VISIBILITY)
    surface_value = _validate_choice("surface", surface, _VALID_SURFACE)

    tips: list[str] = []

    if precip_value in {"light", "moderate", "heavy"}:
        tips.append("Carry an umbrella and wear a water-resistant outer layer.")
    if wind_value == "strong":
        tips.append("Secure outerwear and avoid exposed route segments.")
    if visibility_value in {"reduced", "poor"}:
        tips.append("Add a high-visibility layer and allow a 10-minute travel buffer.")
    if surface_value in {"wet", "slippery"}:
        tips.append("Wear slip-resistant footwear and choose the safer route.")
    if surface_value == "obstructed":
        tips.append("Use an alternate exit path and avoid carrying bulky items.")

    if not tips:
        return [
            "Run a 2-minute physical doorway check immediately before departure.",
            "Carry a compact umbrella and water-resistant outer layer as a no-regret hedge.",
            "Wear slip-resistant footwear and choose the better-lit route if conditions are unclear.",
        ]

    fallback_pool = [
        "Do a final 10-second doorway look before stepping out.",
        "Keep one hand free for stability on stairs and thresholds.",
        "If conditions shift, add a 10-minute travel buffer before critical commitments.",
    ]

    for tip in fallback_pool:
        if len(tips) >= 3:
            break
        if tip not in tips:
            tips.append(tip)

    return tips[:3]


def _load_rows(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []

    rows: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _record_day(ts_value: str) -> str:
    token = str(ts_value or "").strip()
    if "T" in token:
        return token.split("T", 1)[0]
    if " " in token:
        return token.split(" ", 1)[0]
    return token


def remaining_required_slots(log_path: Path, day: str) -> list[str]:
    seen_slots = {
        str(row.get("slot") or "")
        for row in _load_rows(log_path)
        if _record_day(str(row.get("ts") or "")) == day
    }
    return [slot for slot in ("morning", "evening") if slot not in seen_slots]


def cadence_status(log_path: Path, now: datetime) -> dict[str, Any]:
    day = now.date().isoformat()
    remaining = remaining_required_slots(log_path, day)
    completed = [slot for slot in ("morning", "evening") if slot not in remaining]

    clock = now.timetz().replace(tzinfo=None)
    current_window_slot = ""
    if _MORNING_START <= clock <= _MORNING_END:
        current_window_slot = "morning"
    elif _EVENING_START <= clock <= _EVENING_END:
        current_window_slot = "evening"

    should_scan_now = bool(current_window_slot and current_window_slot in remaining)

    overdue: list[str] = []
    if clock > _MORNING_END and "morning" in remaining:
        overdue.append("morning")
    if clock > _EVENING_END and "evening" in remaining:
        overdue.append("evening")

    next_slot = ""
    if remaining:
        if should_scan_now:
            next_slot = current_window_slot
        elif clock < _MORNING_START and "morning" in remaining:
            next_slot = "morning"
        elif clock < _EVENING_START and "evening" in remaining:
            next_slot = "evening"
        elif clock > _EVENING_END:
            next_slot = "morning"
        elif "evening" in remaining:
            next_slot = "evening"
        elif "morning" in remaining:
            next_slot = "morning"

    return {
        "date": day,
        "remaining_slots_today": remaining,
        "completed_slots_today": completed,
        "current_window_slot": current_window_slot,
        "should_scan_now": should_scan_now,
        "overdue_slots_today": overdue,
        "next_slot": next_slot,
        "next_window_local": _WINDOW_RANGES.get(next_slot, ""),
    }


def append_scan_record(
    *,
    log_path: Path,
    now: datetime,
    slot: str,
    precipitation: str,
    wind: str,
    visibility: str,
    surface: str,
    confidence: str,
    notes: str,
) -> dict[str, Any]:
    resolved_slot = choose_slot(now, slot)
    precip_value = _validate_choice("precipitation", precipitation, _VALID_PRECIPITATION)
    wind_value = _validate_choice("wind", wind, _VALID_WIND)
    visibility_value = _validate_choice("visibility", visibility, _VALID_VISIBILITY)
    surface_value = _validate_choice("surface", surface, _VALID_SURFACE)
    confidence_value = _validate_choice("confidence", confidence, _VALID_CONFIDENCE)

    day = now.date().isoformat()
    if resolved_slot in {"morning", "evening"}:
        seen_slots = {
            str(row.get("slot") or "")
            for row in _load_rows(log_path)
            if _record_day(str(row.get("ts") or "")) == day
        }
        if resolved_slot in seen_slots:
            raise DuplicateSlotError(
                f"Slot {resolved_slot!r} already exists for {day} in {log_path}."
            )

    record = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "slot": resolved_slot,
        "precipitation": precip_value,
        "wind": wind_value,
        "visibility": visibility_value,
        "surface": surface_value,
        "action_tips": generate_action_tips(
            precipitation=precip_value,
            wind=wind_value,
            visibility=visibility_value,
            surface=surface_value,
        ),
        "confidence": confidence_value,
        "notes": str(notes or "").strip(),
    }

    if len(record["action_tips"]) != 3:
        raise DoorstepScanError("Action tips must contain exactly 3 items.")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    return record


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doorstep_scan")
    parser.add_argument("--log-path", required=True, help="Path to NDJSON scan log")
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Report cadence status only and do not append a scan record.",
    )
    parser.add_argument("--slot", default="auto", choices=sorted(_VALID_SLOT_INPUTS))
    parser.add_argument("--precipitation", default="unknown", choices=sorted(_VALID_PRECIPITATION))
    parser.add_argument("--wind", default="unknown", choices=sorted(_VALID_WIND))
    parser.add_argument("--visibility", default="unknown", choices=sorted(_VALID_VISIBILITY))
    parser.add_argument("--surface", default="unknown", choices=sorted(_VALID_SURFACE))
    parser.add_argument("--confidence", default="inferred", choices=sorted(_VALID_CONFIDENCE))
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--now",
        default="",
        help="ISO timestamp override for deterministic runs (defaults to local now)",
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

    log_path = Path(args.log_path)
    if args.status_only:
        print(
            json.dumps(
                {
                    "ok": True,
                    "status": cadence_status(log_path, now),
                },
                sort_keys=True,
            )
        )
        return 0

    try:
        record = append_scan_record(
            log_path=log_path,
            now=now,
            slot=args.slot,
            precipitation=args.precipitation,
            wind=args.wind,
            visibility=args.visibility,
            surface=args.surface,
            confidence=args.confidence,
            notes=args.notes,
        )
    except (DoorstepScanError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1

    status = cadence_status(log_path, now)
    print(
        json.dumps(
            {
                "ok": True,
                "record": record,
                "remaining_slots_today": status["remaining_slots_today"],
                "status": status,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
