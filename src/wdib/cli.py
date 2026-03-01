"""CLI entrypoint for WDIB control plane."""

from __future__ import annotations

import argparse
import json
import sys

from .control.human_messages import enqueue_human_message
from .env import load_dotenv, resolve_device_id
from .runtime import run_tick


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wdib")
    sub = parser.add_subparsers(dest="command", required=True)

    tick = sub.add_parser("tick", help="Run one WDIB orchestration cycle")
    tick.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    message = sub.add_parser("message", help="Queue a human message for next WDIB tick")
    message.add_argument("--text", required=True, help="Instruction text from human")
    message.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "tick":
        try:
            result = run_tick()
        except Exception as exc:
            error_payload = {
                "ok": False,
                "error": str(exc),
            }
            print(json.dumps(error_payload, indent=2 if args.pretty else None, sort_keys=True))
            return 1

        payload = {
            "ok": True,
            "result": result,
        }
        print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
        return 0

    if args.command == "message":
        try:
            load_dotenv()
            device_id = resolve_device_id()
            path = enqueue_human_message(device_id, args.text)
        except Exception as exc:
            error_payload = {
                "ok": False,
                "error": str(exc),
            }
            print(json.dumps(error_payload, indent=2 if args.pretty else None, sort_keys=True))
            return 1

        payload = {
            "ok": True,
            "result": {
                "device_id": device_id,
                "human_message_path": str(path),
                "queued": True,
            },
        }
        print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
