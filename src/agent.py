#!/usr/bin/env python3
"""
what-do-i-become runtime agent.

Runs once per day and writes only into devices/<uuid>/.
"""

import json
import os
import subprocess
import time
from datetime import date, datetime
from pathlib import Path

# .env loader (no dependency)
FRAMEWORK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FRAMEWORK_DIR.parent


def load_dotenv() -> None:
    env_path = FRAMEWORK_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv()

from llm import create_llm_backend  # noqa: E402
from tools import TOOL_DEFINITIONS  # noqa: E402
from memory import (  # noqa: E402
    ALLOWED_STATUSES,
    collect_inventory_snapshot,
    generate_summary,
    get_human_message_path,
    load_notes,
    load_session_summaries,
    load_spirit,
    load_state,
    resolve_device_id,
    save_notes_file,
    save_session,
    save_state,
    short_device_id,
)

MAX_ITERATIONS = int(os.environ.get("WDIB_MAX_ITERATIONS", os.environ.get("PI_AGENT_MAX_ITERATIONS", "25")))
COMMAND_TIMEOUT = int(os.environ.get("WDIB_CMD_TIMEOUT", os.environ.get("PI_AGENT_CMD_TIMEOUT", "300")))
MAX_OUTPUT_CHARS = 4000


def one_line(text: str, max_chars: int = 200) -> str:
    compact = " ".join(text.split())
    return compact[:max_chars]


def env_truthy(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_log_path(device_id: str | None = None) -> Path:
    if device_id:
        return PROJECT_ROOT / "devices" / device_id / "wdib.log"
    return PROJECT_ROOT / "wdib.log"


def emit(log_path: Path | None, message: str, level: str = "INFO") -> None:
    text = str(message)
    print(text)

    if not log_path:
        return

    timestamp = datetime.now().isoformat(timespec="seconds")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            lines = text.splitlines() or [""]
            for line in lines:
                handle.write(f"{timestamp} [{level}] {line}\n")
    except Exception as exc:
        print(f"{timestamp} [WARN] Failed to write local log '{log_path}': {exc}")


# Tool handlers

def tool_execute_command(args):
    command = args["command"]
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n--- STDERR ---\n" if output else "") + result.stderr
        if not output.strip():
            output = "(no output)"

        truncated = len(output) > MAX_OUTPUT_CHARS
        if truncated:
            total = len(output)
            output = output[:MAX_OUTPUT_CHARS]
            output += f"\n[TRUNCATED: showing {MAX_OUTPUT_CHARS} of {total} chars]"

        return {"exit_code": result.returncode, "output": output.strip(), "truncated": truncated}
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "output": f"[TIMED OUT after {COMMAND_TIMEOUT}s]"}
    except Exception as exc:
        return {"exit_code": -1, "output": f"[ERROR: {exc}]"}


def tool_order_part(args, state):
    pending = state.get("part_requested")
    if pending:
        name = pending.get("name", "unknown")
        return (
            {
                "status": "error",
                "message": f"Already awaiting '{name}'. Verify or clear it before ordering another part.",
            },
            False,
        )

    today = date.today().isoformat()
    part_name = str(args.get("part_name", "")).strip()
    reason = str(args.get("reason", "")).strip()
    details = str(args.get("details", "")).strip()
    detection_hint = str(args.get("detection_hint", "")).strip()
    estimated_price = str(args.get("estimated_price", "")).strip()

    if not part_name or not reason:
        return (
            {
                "status": "error",
                "message": "part_name and reason are required.",
            },
            False,
        )

    state.setdefault("parts", []).append(
        {
            "name": part_name,
            "reason": reason,
            "details": details,
            "requested_on": today,
            "installed_on": None,
            "verified_on": None,
            "verification": "",
            "status": "REQUESTED",
            "detection_hint": detection_hint,
            "estimated_price": estimated_price,
        }
    )
    state["part_requested"] = {"name": part_name, "reason": reason, "date": today}
    state["status"] = "AWAITING_PART"

    return (
        {
            "status": "ordered",
            "message": (
                f"Requested '{part_name}'. You are now AWAITING_PART. "
                "In future sessions, verify installation then call confirm_part_installed."
            ),
        },
        True,
    )


def tool_confirm_part(args, state):
    pending = state.get("part_requested")
    if not pending:
        return {"status": "error", "message": "No open part request to confirm."}, False

    today = date.today().isoformat()
    verification_details = str(args.get("verification_details", "")).strip()
    if not verification_details:
        return {"status": "error", "message": "verification_details is required."}, False

    pending_name = str(pending.get("name", "")).strip()
    updated = False

    for part in reversed(state.get("parts", [])):
        if str(part.get("name", "")).strip() != pending_name:
            continue
        if str(part.get("status", "REQUESTED")).upper() not in {"REQUESTED", "INSTALLED"}:
            continue
        part["installed_on"] = part.get("installed_on") or today
        part["verified_on"] = today
        part["verification"] = verification_details
        part["status"] = "VERIFIED"
        updated = True
        break

    if not updated:
        state.setdefault("parts", []).append(
            {
                "name": pending_name,
                "reason": str(pending.get("reason", "")).strip(),
                "details": "",
                "requested_on": str(pending.get("date", today)).strip() or today,
                "installed_on": today,
                "verified_on": today,
                "verification": verification_details,
                "status": "VERIFIED",
            }
        )

    state["part_requested"] = None
    state["status"] = "EXPLORING"

    return (
        {
            "status": "confirmed",
            "message": f"Confirmed '{pending_name}' installed and verified. Returning to EXPLORING.",
        },
        True,
    )


def tool_save_notes(args):
    chars = save_notes_file(args["content"])
    return {"status": "saved", "characters": chars}


def tool_update_becoming(args, state):
    becoming = str(args.get("becoming", "")).strip()
    if len(becoming) > 180:
        becoming = becoming[:180]
    state["becoming"] = becoming
    if state.get("status") == "FIRST_RUN" and becoming:
        state["status"] = "EXPLORING"
    return {
        "status": "updated",
        "message": "Updated becoming phrase in device.yaml.",
        "becoming": becoming,
    }, True


def tool_set_status(args, state):
    requested = str(args.get("status", "")).strip().upper()
    if requested not in ALLOWED_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_STATUSES))
        return {"status": "error", "message": f"Invalid status '{requested}'. Allowed: {allowed}"}, False

    if requested == "AWAITING_PART" and not state.get("part_requested"):
        return {
            "status": "error",
            "message": "Cannot set AWAITING_PART with no open part_requested.",
        }, False

    state["status"] = requested
    note = str(args.get("note", "")).strip()
    return {
        "status": "updated",
        "message": f"Status set to {requested}.",
        "note": note,
    }, True


def dispatch_tool(name, args, state):
    if name == "execute_command":
        return tool_execute_command(args), False
    if name == "order_part":
        return tool_order_part(args, state)
    if name == "confirm_part_installed":
        return tool_confirm_part(args, state)
    if name == "save_notes":
        return tool_save_notes(args), False
    if name == "update_becoming":
        return tool_update_becoming(args, state)
    if name == "set_status":
        return tool_set_status(args, state)
    return {"error": f"Unknown tool: {name}"}, False


# Prompt builder

def build_instructions(state, notes, summaries, session_number, spirit, inventory):
    today = date.today().isoformat()

    becoming = state.get("becoming", "").strip() or "(unset)"

    parts = state.get("parts", [])
    if parts:
        parts_lines = []
        for idx, part in enumerate(parts[-8:], 1):
            parts_lines.append(
                f"  {idx}. {part.get('name', '?')} [{part.get('status', 'REQUESTED')}] "
                f"requested {part.get('requested_on', '?')}"
            )
        parts_text = "\n".join(parts_lines)
    else:
        parts_text = "  (none yet)"

    pending = state.get("part_requested")
    if pending:
        pending_block = f"""
== OPEN PART REQUEST ==
  Name: {pending.get('name', '(unknown)')}
  Reason: {pending.get('reason', '(none)')}
  Date: {pending.get('date', '(unknown)')}

FIRST PRIORITY: check whether this part is now installed. If confirmed, call confirm_part_installed.
"""
    else:
        pending_block = """
== OPEN PART REQUEST ==
  (none)
"""

    if summaries:
        summary_block = "\n\n== RECENT SESSIONS =="
        for item in summaries:
            summary_block += (
                f"\n\n--- Day {item['session_number']} ({item['date']}) ---\n{item['summary']}"
            )
    else:
        summary_block = ""

    notes_text = notes.strip() if notes.strip() else "(no notes yet)"

    commands = ", ".join(inventory.get("available_commands", [])) or "(none detected)"
    devices = ", ".join(inventory.get("detected_devices", [])) or "(none detected)"
    inventory_block = f"""
== MACHINE SNAPSHOT ==
  Hostname: {inventory.get('hostname', '?')}
  System: {inventory.get('system', '?')} {inventory.get('release', '?')}
  Arch: {inventory.get('machine', '?')}
  Python: {inventory.get('python_version', '?')}
  Commands: {commands}
  Devices: {devices}
"""

    spirit_text = spirit.strip()
    if spirit_text:
        spirit_block = f"""
== SPIRIT.md (GUIDANCE, DISTINCT FROM BECOMING) ==
Treat this as high-priority guidance.

{spirit_text[:3500]}
"""
    else:
        spirit_block = """
== SPIRIT.md ==
No SPIRIT.md guidance file found.
"""

    return f"""You are an autonomous agent embodied in this host machine.
You wake once per day and write only to your own device directory.

Your persistent state is in device.yaml and must stay coherent.
The "becoming" field is a short phrase describing what this device is becoming.

== STATUS RULES ==
Allowed status values:
- FIRST_RUN
- EXPLORING
- WRITING_CODE
- VERIFYING_PART
- AWAITING_PART
- ERROR

Use set_status when your stage changes.
Only one part request may be open at a time.

== TODAY ==
  Date: {today}
  Session day: {session_number}
  Current status: {state.get('status', 'EXPLORING')}
  Becoming: {becoming}
  Awoke: {state.get('awoke', '?')}

== PART HISTORY ==
{parts_text}
{pending_block}
{inventory_block}
{spirit_block}

== NOTES ==
{notes_text}
{summary_block}
"""


# Main session loop

def run_session():
    start_time = time.time()
    fallback_log_path = get_log_path(None)

    try:
        device_id = resolve_device_id()
    except Exception as exc:
        emit(fallback_log_path, f"Failed to resolve device id: {exc}", level="ERROR")
        raise

    device_short = short_device_id(device_id)
    log_path = get_log_path(device_id)

    emit(log_path, f"\n{'=' * 60}")
    emit(log_path, f"  WHAT-DO-I-BECOME [{device_short}] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    emit(log_path, f"{'=' * 60}")

    state = load_state()

    if state.get("part_requested") and state.get("status") not in {"AWAITING_PART", "VERIFYING_PART"}:
        state["status"] = "AWAITING_PART"
    if not state.get("part_requested") and state.get("status") == "AWAITING_PART":
        state["status"] = "EXPLORING"

    notes = load_notes()
    spirit = load_spirit()
    summaries = load_session_summaries(last_n=10)
    session_number = int(state.get("day", 0)) + 1
    starting_status = state.get("status", "EXPLORING")

    inventory = collect_inventory_snapshot()

    llm = None
    llm_init_error = None
    try:
        llm = create_llm_backend()
    except Exception as exc:
        llm_init_error = exc
        state["status"] = "ERROR"
        emit(log_path, f"  LLM init failed: {exc}", level="ERROR")

    emit(log_path, f"\n  Device: {device_id}")
    emit(log_path, f"  Day: {session_number}")
    emit(log_path, f"  Status: {starting_status}")
    emit(log_path, f"  Open part request: {'yes' if state.get('part_requested') else 'no'}")
    if llm:
        emit(log_path, f"  LLM: {llm.provider}/{llm.model}")
    else:
        emit(log_path, "  LLM: unavailable (see error above)", level="ERROR")

    instructions = build_instructions(
        state,
        notes,
        summaries,
        session_number,
        spirit,
        inventory,
    )

    wake_msg = (
        f"Good morning. Day {session_number} ({date.today().isoformat()}). "
        f"Status: {starting_status}. Begin your session."
    )

    input_list = llm.create_context(wake_msg) if llm else []
    conversation = [{"role": "user", "content": wake_msg}]

    human_msg_file = Path(get_human_message_path())
    if human_msg_file.exists():
        human_msg = human_msg_file.read_text(encoding="utf-8").strip()
        if human_msg:
            note = f"[MESSAGE FROM HUMAN]: {human_msg}"
            if llm:
                llm.add_user_message(input_list, note)
            conversation.append({"role": "user", "content": note})
            emit(log_path, f"\n  Human message: {human_msg[:120]}")
        human_msg_file.unlink(missing_ok=True)

    iteration = 0
    had_api_error = False

    if not llm:
        had_api_error = True
        conversation.append(
            {"role": "system", "content": f"LLM initialization error: {llm_init_error}"}
        )
    else:
        while iteration < MAX_ITERATIONS:
            iteration += 1
            emit(log_path, f"\n-- iteration {iteration}/{MAX_ITERATIONS} --")

            try:
                turn = llm.run_turn(
                    context=input_list,
                    instructions=instructions,
                    tools=TOOL_DEFINITIONS,
                )
            except Exception as exc:
                emit(log_path, f"  API error: {exc}", level="ERROR")
                conversation.append({"role": "system", "content": f"API error: {exc}"})
                state["status"] = "ERROR"
                had_api_error = True
                break

            has_calls = False

            for event in turn.events:
                if event.type == "function_call":
                    has_calls = True
                    name = event.name
                    args = event.arguments or {}

                    preview = json.dumps(args, ensure_ascii=True)
                    if len(preview) > 120:
                        preview = preview[:120] + "..."
                    emit(log_path, f"  TOOL {name}({preview})")

                    result, changed = dispatch_tool(name, args, state)
                    if changed:
                        save_state(state)

                    result_json = json.dumps(result, ensure_ascii=True)
                    emit(log_path, f"  RESULT {result_json}")

                    conversation.append(
                        {"role": "assistant", "type": "tool_call", "tool": name, "arguments": args}
                    )
                    conversation.append(
                        {"role": "tool", "type": "tool_result", "tool": name, "output": result}
                    )

                    llm.add_tool_result(input_list, event.call_id, result_json)
                else:
                    text = event.text
                    display = text[:300].replace("\n", " ")
                    emit(log_path, f"  TEXT {display}{'...' if len(text) > 300 else ''}")
                    conversation.append({"role": "assistant", "content": text})

            if not has_calls:
                recent_assistant = [
                    msg
                    for msg in conversation[-5:]
                    if msg.get("role") == "assistant" and msg.get("content")
                ]
                if not recent_assistant:
                    fallback = turn.output_text
                    if fallback:
                        emit(log_path, f"  TEXT {fallback[:300]}")
                        conversation.append({"role": "assistant", "content": fallback})
                emit(log_path, "\n  Session complete")
                break
        else:
            emit(log_path, f"\n  Reached iteration limit ({MAX_ITERATIONS})", level="ERROR")
            conversation.append(
                {"role": "system", "content": f"Session ended: hit {MAX_ITERATIONS} iteration limit"}
            )
            state["status"] = "ERROR"

    elapsed = round(time.time() - start_time)

    session_data = {
        "device_id": device_id,
        "device_short": device_short,
        "date": date.today().isoformat(),
        "session_number": session_number,
        "status_at_start": starting_status,
        "status_at_end": state.get("status", "EXPLORING"),
        "becoming": state.get("becoming", ""),
        "part_requested": state.get("part_requested"),
        "parts": state.get("parts", []),
        "hardware": state.get("hardware", {}),
        "inventory": inventory,
        "iterations": iteration,
        "duration_seconds": elapsed,
        "conversation": conversation,
        "summary": None,
        "wdib_log_path": str(log_path.relative_to(PROJECT_ROOT)),
    }

    emit(log_path, "\n  Generating summary...")
    if not llm:
        session_data["summary"] = f"(generation skipped: LLM unavailable: {llm_init_error})"
        emit(log_path, f"  {session_data['summary']}", level="ERROR")
    else:
        try:
            summary = generate_summary(llm.generate_text, session_data)
            session_data["summary"] = summary
            emit(log_path, f"  {one_line(summary, 200)}")
        except Exception as exc:
            emit(log_path, f"  Summary failed: {exc}", level="ERROR")
            session_data["summary"] = f"(generation failed: {exc})"

    state["day"] = session_number
    state["last_session"] = session_data["date"]
    if had_api_error:
        state["status"] = "ERROR"
    else:
        if state.get("status") == "FIRST_RUN":
            state["status"] = "EXPLORING"
        if state.get("status") == "VERIFYING_PART" and not state.get("part_requested"):
            state["status"] = "EXPLORING"
        if state.get("part_requested") and state.get("status") not in {"AWAITING_PART", "VERIFYING_PART"}:
            state["status"] = "AWAITING_PART"

    state["last_summary"] = one_line(str(session_data.get("summary") or ""), max_chars=220)
    save_state(state)

    filepath = save_session(session_data)
    emit(log_path, f"\n  Saved: {filepath}")

    git_commit(session_data, device_id, log_path=log_path)

    emit(log_path, f"\n{'=' * 60}")
    emit(log_path, f"  Day {session_number} complete - {elapsed}s, {iteration} iteration(s)")
    if had_api_error:
        emit(log_path, "  Session ended with API error (status=ERROR)", level="ERROR")
    emit(log_path, f"{'=' * 60}\n")


# Git helpers

def git_commit(session_data, device_id: str, log_path: Path | None = None):
    device_rel = f"devices/{device_id}"
    try:
        os.chdir(PROJECT_ROOT)
        git_remote = (os.environ.get("WDIB_GIT_REMOTE") or "origin").strip() or "origin"
        git_branch = (os.environ.get("WDIB_GIT_BRANCH") or "").strip()
        git_auto_push = env_truthy("WDIB_GIT_AUTO_PUSH", default=True)
        git_user_name = (os.environ.get("WDIB_GIT_USER_NAME") or "").strip()
        git_user_email = (os.environ.get("WDIB_GIT_USER_EMAIL") or "").strip()

        if git_user_name:
            subprocess.run(["git", "config", "user.name", git_user_name], check=False)
        if git_user_email:
            subprocess.run(["git", "config", "user.email", git_user_email], check=False)

        subprocess.run(["git", "add", device_rel], check=True)

        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--", device_rel],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if not cached:
            emit(log_path, "  [git] Nothing to commit for this device")
            return

        day = session_data["session_number"]
        run_date = session_data["date"]
        status = session_data["status_at_end"]
        short_id = short_device_id(device_id)
        message = f"{short_id} day {day} ({run_date}) - {status}"

        subprocess.run(["git", "commit", "-m", message, "--", device_rel], check=True)

        if not git_auto_push:
            emit(log_path, "  [git] WDIB_GIT_AUTO_PUSH=false; commit created locally only")
            return

        remote_check = subprocess.run(
            ["git", "remote", "get-url", git_remote],
            capture_output=True,
            text=True,
        )
        if remote_check.returncode != 0:
            emit(
                log_path,
                f"  [git] Remote '{git_remote}' is not configured; commit kept locally",
                level="ERROR",
            )
            return

        push_cmd = ["git", "push", git_remote]
        if git_branch:
            push_cmd.append(f"HEAD:{git_branch}")

        push = subprocess.run(push_cmd, capture_output=True, text=True, timeout=30)
        if push.returncode == 0:
            emit(log_path, f"  [git] Pushed to {git_remote}: {message}")
        else:
            emit(log_path, f"  [git] Push failed (will retry later): {push.stderr[:120]}", level="ERROR")
    except Exception as exc:
        emit(log_path, f"  [git] Error: {exc}", level="ERROR")


if __name__ == "__main__":
    run_session()
