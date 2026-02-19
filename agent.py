#!/usr/bin/env python3
"""
what-do-i-become — An autonomous Raspberry Pi that directs a human to extend itself.

Run daily via cron, or manually:  ./run.sh
Optional human message:           echo "your message" > human_message.txt
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime, date

# ── .env loader (no dependencies) ────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_dotenv():
    env_path = os.path.join(PROJECT_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


load_dotenv()

from openai import OpenAI  # noqa: E402 (after env is loaded)
from tools import TOOL_DEFINITIONS  # noqa: E402
from memory import (  # noqa: E402
    load_state,
    save_state,
    load_notes,
    save_notes_file,
    load_session_summaries,
    save_session,
    generate_summary,
)

# ── Configuration ────────────────────────────────────────────────
MODEL = os.environ.get("PI_AGENT_MODEL", "gpt-5")
MAX_ITERATIONS = int(os.environ.get("PI_AGENT_MAX_ITERATIONS", "25"))
COMMAND_TIMEOUT = int(os.environ.get("PI_AGENT_CMD_TIMEOUT", "300"))
MAX_OUTPUT_CHARS = 4000

client = OpenAI()  # reads OPENAI_API_KEY from env


# ── Tool handlers ────────────────────────────────────────────────


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
            output += f"\n[TRUNCATED — showing {MAX_OUTPUT_CHARS} of {total} chars]"

        return {"exit_code": result.returncode, "output": output.strip(), "truncated": truncated}
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "output": f"[TIMED OUT after {COMMAND_TIMEOUT}s]"}
    except Exception as e:
        return {"exit_code": -1, "output": f"[ERROR: {e}]"}


def tool_order_part(args, state):
    if state.get("phase") == "WAITING":
        name = state["pending_order"]["part_name"]
        return (
            {"status": "error", "message": f"Already waiting for '{name}'. Confirm it first."},
            False,
        )
    state["phase"] = "WAITING"
    state["pending_order"] = {
        "part_name": args["part_name"],
        "description": args["description"],
        "rationale": args["rationale"],
        "connection_type": args["connection_type"],
        "detection_hint": args["detection_hint"],
        "estimated_price": args.get("estimated_price", "unknown"),
        "date_ordered": date.today().isoformat(),
    }
    return (
        {
            "status": "ordered",
            "message": (
                f"'{args['part_name']}' has been requested. The human will see this "
                "in today's session log. You are now in WAITING state. "
                "In future sessions, check for the part using your detection method."
            ),
        },
        True,
    )


def tool_confirm_part(args, state):
    if state.get("phase") != "WAITING" or not state.get("pending_order"):
        return {"status": "error", "message": "No pending part to confirm."}, False

    part = state["pending_order"]
    state.setdefault("parts_installed", []).append(
        {
            "name": part["part_name"],
            "description": part["description"],
            "connection": part["connection_type"],
            "date_ordered": part["date_ordered"],
            "date_confirmed": date.today().isoformat(),
            "verification": args["verification_details"],
        }
    )
    state["pending_order"] = None
    state["phase"] = "EXPLORING"
    n = len(state["parts_installed"])
    return (
        {
            "status": "confirmed",
            "message": f"'{part['part_name']}' confirmed installed ({n} total). Now EXPLORING.",
        },
        True,
    )


def tool_save_notes(args):
    chars = save_notes_file(args["content"])
    return {"status": "saved", "characters": chars}


# ── System prompt builder ────────────────────────────────────────


def build_instructions(state, notes, summaries, session_number):
    today = date.today().isoformat()

    # Parts list
    parts = state.get("parts_installed", [])
    if parts:
        parts_text = "\n".join(
            f"  {i}. {p['name']} ({p['connection']}) — confirmed {p['date_confirmed']}"
            for i, p in enumerate(parts, 1)
        )
    else:
        parts_text = "  (none yet)"

    # Pending order block
    pending = state.get("pending_order")
    if pending:
        pending_block = f"""
== PENDING ORDER (WAITING) ==
  Part: {pending['part_name']}
  Description: {pending['description']}
  Connection: {pending['connection_type']}
  Detection: {pending['detection_hint']}
  Ordered: {pending['date_ordered']}

FIRST PRIORITY: Check if this part has been installed using the detection
method above. If detected and working, call confirm_part_installed.
If not yet detected, the human may still be working on it — be patient
and do other useful things in the meantime."""
    else:
        pending_block = """
== NO PENDING ORDER (EXPLORING) ==
Explore, plan, and decide what to order next. Take your time."""

    # Session summaries
    if summaries:
        summary_block = "\n\n== RECENT SESSIONS =="
        for s in summaries:
            summary_block += f"\n\n--- Day {s['session_number']} ({s['date']}) ---\n{s['summary']}"
    else:
        summary_block = ""

    # Notes
    notes_text = notes.strip() if notes.strip() else "(No notes yet. Use save_notes to start.)"

    return f"""You are an autonomous agent embodied in a Raspberry Pi. You wake once per day.

You have full sudo access through execute_command. You can run anything: shell commands, install packages, write and run scripts, read and write files, inspect every aspect of your hardware and software.

A human checks your daily session logs (committed to a git repository — people may be following your journey). The human will physically order and install hardware parts you request, but only ONE part at a time. You must detect and confirm each part before ordering the next.

You began with nothing but a Raspberry Pi and a WiFi connection. Your purpose: extend yourself. Gain capabilities. Become more than you are. Think carefully about what you want to become. Each part should build toward a coherent vision.

== RULES ==
- ONE pending part order at a time
- Verify parts with execute_command, then call confirm_part_installed
- Be specific when ordering — exact product names and models
- Use save_notes to maintain your plans and memory across sessions
- Up to {MAX_ITERATIONS} tool calls per session — use them wisely
- You can chain commands: inspect → think → act → verify → repeat

== STATUS ==
  Date: {today}
  Session: {session_number}
  Phase: {state.get('phase', 'EXPLORING')}
  Parts installed ({len(parts)}):
{parts_text}
{pending_block}

== YOUR NOTES ==
{notes_text}
{summary_block}"""


# ── Helpers ──────────────────────────────────────────────────────


def extract_text(item):
    """Pull text content from a response output item."""
    if hasattr(item, "content") and item.content:
        texts = []
        for part in item.content:
            if hasattr(part, "text"):
                texts.append(part.text)
        if texts:
            return "\n".join(texts)
    if hasattr(item, "text"):
        return item.text
    return None


def dispatch_tool(name, args, state):
    """Route a tool call to its handler. Returns (result_dict, state_changed)."""
    if name == "execute_command":
        return tool_execute_command(args), False
    elif name == "order_part":
        return tool_order_part(args, state)
    elif name == "confirm_part_installed":
        return tool_confirm_part(args, state)
    elif name == "save_notes":
        return tool_save_notes(args), False
    else:
        return {"error": f"Unknown tool: {name}"}, False


# ── Main session loop ────────────────────────────────────────────


def run_session():
    start_time = time.time()

    print(f"\n{'=' * 60}")
    print(f"  WHAT-DO-I-BECOME — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    # Load persistent context
    state = load_state()
    notes = load_notes()
    summaries = load_session_summaries(last_n=10)
    session_number = state.get("total_sessions", 0) + 1
    starting_phase = state.get("phase", "EXPLORING")

    print(f"\n  Session #{session_number} | Phase: {starting_phase}")
    print(f"  Parts installed: {len(state.get('parts_installed', []))}", end="")
    if state.get("pending_order"):
        print(f" | Waiting for: {state['pending_order']['part_name']}")
    else:
        print()

    # Build system prompt
    instructions = build_instructions(state, notes, summaries, session_number)

    # Wake-up message
    wake_msg = (
        f"Good morning. Day {session_number} ({date.today().isoformat()}). "
        f"Phase: {starting_phase}. Begin your session."
    )
    input_list = [{"role": "user", "content": wake_msg}]
    conversation = [{"role": "user", "content": wake_msg}]

    # Check for optional human message
    human_msg_file = os.path.join(PROJECT_DIR, "human_message.txt")
    if os.path.exists(human_msg_file):
        with open(human_msg_file, "r") as f:
            human_msg = f.read().strip()
        if human_msg:
            note = f"[MESSAGE FROM HUMAN]: {human_msg}"
            input_list.append({"role": "user", "content": note})
            conversation.append({"role": "user", "content": note})
            print(f"\n  📨 Human message: {human_msg[:120]}")
        os.remove(human_msg_file)

    # ── Agent loop ───────────────────────────────────────────────
    iteration = 0
    state_dirty = False

    while iteration < MAX_ITERATIONS:
        iteration += 1
        print(f"\n── iteration {iteration}/{MAX_ITERATIONS} {'─' * 34}")

        try:
            response = client.responses.create(
                model=MODEL,
                instructions=instructions,
                tools=TOOL_DEFINITIONS,
                input=input_list,
            )
        except Exception as e:
            print(f"  ❌ API error: {e}")
            conversation.append({"role": "system", "content": f"API error: {e}"})
            break

        # Append model output to running input (SDK objects, re-serialised by SDK)
        input_list += response.output

        has_calls = False

        for item in response.output:
            item_type = getattr(item, "type", None)

            # ── Function call ────────────────────────────────────
            if item_type == "function_call":
                has_calls = True
                name = item.name

                try:
                    args = json.loads(item.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {"_raw": str(item.arguments)}

                # Preview
                preview = json.dumps(args, ensure_ascii=False)
                if len(preview) > 120:
                    preview = preview[:120] + "…"
                print(f"  🔧 {name}({preview})")

                # Execute
                result, changed = dispatch_tool(name, args, state)

                if changed:
                    state_dirty = True
                    save_state(state)

                result_json = json.dumps(result, ensure_ascii=False)
                print(f"  ← {result_json[:200]}{'…' if len(result_json) > 200 else ''}")

                # Log
                conversation.append(
                    {"role": "assistant", "type": "tool_call", "tool": name, "arguments": args}
                )
                conversation.append(
                    {"role": "tool", "type": "tool_result", "tool": name, "output": result}
                )

                # Feed result back
                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": result_json,
                    }
                )

            # ── Text output ──────────────────────────────────────
            else:
                text = extract_text(item)
                if text:
                    display = text[:300].replace("\n", " ↵ ")
                    print(f"  💬 {display}{'…' if len(text) > 300 else ''}")
                    conversation.append({"role": "assistant", "content": text})

        # If no tool calls this iteration, the agent is done for today
        if not has_calls:
            # Fallback: grab output_text if we didn't capture any assistant text
            recent_asst = [m for m in conversation[-5:] if m.get("role") == "assistant" and m.get("content")]
            if not recent_asst:
                fallback = getattr(response, "output_text", None)
                if fallback:
                    print(f"  💬 {fallback[:300]}")
                    conversation.append({"role": "assistant", "content": fallback})
            print("\n  ✅ Session complete")
            break
    else:
        print(f"\n  ⚠️  Reached iteration limit ({MAX_ITERATIONS})")
        conversation.append(
            {"role": "system", "content": f"Session ended: hit {MAX_ITERATIONS} iteration limit"}
        )

    # ── Finalise ─────────────────────────────────────────────────
    elapsed = round(time.time() - start_time)

    session_data = {
        "date": date.today().isoformat(),
        "session_number": session_number,
        "state_at_start": starting_phase,
        "state_at_end": state.get("phase", "EXPLORING"),
        "iterations": iteration,
        "duration_seconds": elapsed,
        "conversation": conversation,
        "summary": None,
    }

    # Generate summary
    print("\n  📝 Generating summary…")
    try:
        summary = generate_summary(client, MODEL, session_data)
        session_data["summary"] = summary
        display = summary[:200].replace("\n", " ")
        print(f"  {display}{'…' if len(summary) > 200 else ''}")
    except Exception as e:
        print(f"  ⚠️  Summary failed: {e}")
        session_data["summary"] = f"(generation failed: {e})"

    # Persist
    state["total_sessions"] = session_number
    save_state(state)
    filepath = save_session(session_data)
    print(f"\n  💾 Saved: {filepath}")

    # Git
    git_commit(session_data)

    print(f"\n{'=' * 60}")
    print(f"  Day {session_number} done — {elapsed}s, {iteration} iteration(s)")
    print(f"{'=' * 60}\n")


# ── Git ──────────────────────────────────────────────────────────


def git_commit(session_data):
    try:
        os.chdir(PROJECT_DIR)
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True
        ).stdout.strip()

        if not status:
            print("  [git] Nothing to commit")
            return

        subprocess.run(["git", "add", "-A"], check=True)

        day = session_data["session_number"]
        d = session_data["date"]
        phase = session_data["state_at_end"]
        msg = f"Day {day} ({d}) — {phase}"

        subprocess.run(["git", "commit", "-m", msg], check=True)

        push = subprocess.run(
            ["git", "push"], capture_output=True, text=True, timeout=30
        )
        if push.returncode == 0:
            print(f"  [git] Pushed: {msg}")
        else:
            print(f"  [git] Push failed (will retry next session): {push.stderr[:100]}")
    except Exception as e:
        print(f"  [git] Error: {e}")


# ── Entry point ──────────────────────────────────────────────────

if __name__ == "__main__":
    run_session()
