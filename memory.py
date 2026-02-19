# memory.py — Persistence layer for state, notes, and session logs

import os
import yaml
from datetime import date
from pathlib import Path

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(PROJECT_DIR, "sessions")
STATE_FILE = os.path.join(PROJECT_DIR, "state.yaml")
NOTES_FILE = os.path.join(PROJECT_DIR, "notes.md")
MAX_NOTES_CHARS = 3000


# ── YAML formatting ─────────────────────────────────────────────
# Use literal block scalars for multiline strings so YAML is readable

def _str_representer(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)

yaml.add_representer(str, _str_representer)


# ── Directory setup ──────────────────────────────────────────────

def ensure_dirs():
    os.makedirs(SESSIONS_DIR, exist_ok=True)


# ── State ────────────────────────────────────────────────────────

def load_state():
    ensure_dirs()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = yaml.safe_load(f)
            if isinstance(state, dict):
                return state
    return {
        "phase": "EXPLORING",
        "parts_installed": [],
        "pending_order": None,
        "total_sessions": 0,
        "first_boot": date.today().isoformat(),
    }


def save_state(state):
    ensure_dirs()
    with open(STATE_FILE, "w") as f:
        yaml.dump(state, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


# ── Notes ────────────────────────────────────────────────────────

def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r") as f:
            return f.read()
    return ""


def save_notes_file(content):
    if len(content) > MAX_NOTES_CHARS:
        content = content[:MAX_NOTES_CHARS] + "\n\n[TRUNCATED TO FIT BUDGET]"
    with open(NOTES_FILE, "w") as f:
        f.write(content)
    return len(content)


# ── Sessions ─────────────────────────────────────────────────────

def load_session_summaries(last_n=10):
    ensure_dirs()
    files = sorted(Path(SESSIONS_DIR).glob("day_*.yaml"))
    summaries = []
    for fp in files[-(last_n):]:
        try:
            with open(fp, "r") as f:
                data = yaml.safe_load(f)
            if data and data.get("summary"):
                summaries.append({
                    "date": data.get("date", "?"),
                    "session_number": data.get("session_number", "?"),
                    "summary": data.get("summary", ""),
                })
        except Exception:
            continue
    return summaries


def save_session(session_log):
    ensure_dirs()
    num = session_log["session_number"]
    d = session_log["date"]
    filename = f"day_{num:03d}_{d}.yaml"
    filepath = os.path.join(SESSIONS_DIR, filename)
    with open(filepath, "w") as f:
        yaml.dump(
            session_log,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )
    return filepath


def generate_summary(client, model, session_log):
    """Ask the LLM to summarise a session for future context."""
    lines = []
    for msg in session_log.get("conversation", []):
        role = msg.get("role", "?")
        mtype = msg.get("type", "")
        if mtype == "tool_call":
            args_str = str(msg.get("arguments", ""))[:200]
            lines.append(f"[CALLED {msg.get('tool')}] {args_str}")
        elif mtype == "tool_result":
            out = msg.get("output", {})
            if isinstance(out, dict):
                preview = out.get("output", out.get("message", str(out)))[:300]
            else:
                preview = str(out)[:300]
            lines.append(f"[RESULT {msg.get('tool')}] {preview}")
        else:
            content = str(msg.get("content", ""))[:400]
            lines.append(f"[{role.upper()}] {content}")

    transcript = "\n".join(lines)
    # Cap transcript size for the summary call
    if len(transcript) > 6000:
        transcript = transcript[:6000] + "\n[TRANSCRIPT TRUNCATED FOR SUMMARY]"

    response = client.responses.create(
        model=model,
        instructions=(
            "Summarise this what-do-i-become session in 2-3 concise paragraphs. "
            "Include: what the agent explored or discovered, actions taken, "
            "decisions or plans made, any parts ordered or confirmed, and the "
            "ending state. Be factual and specific. No editorialising."
        ),
        input=[{"role": "user", "content": f"Session transcript:\n\n{transcript}"}],
    )
    return response.output_text
