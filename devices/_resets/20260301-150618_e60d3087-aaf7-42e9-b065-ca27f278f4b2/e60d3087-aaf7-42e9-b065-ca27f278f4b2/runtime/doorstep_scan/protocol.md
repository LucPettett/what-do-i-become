# Doorstep Conditions Scan Protocol

Purpose: reduce avoidable departure disruptions with a short local check and three concrete actions.

Cadence (local time):
- Morning scan window: 06:30-09:00
- Evening scan window: 17:00-20:00

2-minute doorstep checklist:
- Precipitation: none | light | moderate | heavy
- Wind: calm | breezy | strong
- Visibility: clear | reduced | poor
- Walking surface: dry | damp | wet | slippery | obstructed

Action-tip rules (publish exactly 3 tips):
- If precipitation is light/moderate/heavy: carry an umbrella and wear a water-resistant outer layer.
- If wind is strong: secure outerwear and avoid exposed route segments.
- If visibility is reduced/poor: add a high-visibility layer and allow a 10-minute travel buffer.
- If surface is wet/slippery: wear slip-resistant footwear and choose the safer route.
- If surface is obstructed: use an alternate exit path and avoid carrying bulky items.
- If all conditions are clear: normal departure, plus a lightweight backup layer.

Fallback when machine sensing is unavailable:
- Run a human-observed doorstep check immediately before leaving.
- Mark confidence as `observed` only when a person performed the checklist.
- Use confidence `unknown` for setup/default entries with no direct observation.

Execution command (from repo root):

```bash
PYTHONPATH=src python3 -m wdib.control.doorstep_scan \
  --log-path devices/e60d3087-aaf7-42e9-b065-ca27f278f4b2/runtime/doorstep_scan/scan_log_$(date +%F).ndjson \
  --slot auto \
  --precipitation <none|light|moderate|heavy|unknown> \
  --wind <calm|breezy|strong|unknown> \
  --visibility <clear|reduced|poor|unknown> \
  --surface <dry|damp|wet|slippery|obstructed|unknown> \
  --confidence <observed|inferred|unknown> \
  --notes "Short context"
```

Cadence status command (no write):

```bash
PYTHONPATH=src python3 -m wdib.control.doorstep_scan \
  --log-path devices/e60d3087-aaf7-42e9-b065-ca27f278f4b2/runtime/doorstep_scan/scan_log_$(date +%F).ndjson \
  --status-only
```

Status interpretation:
- `should_scan_now=true`: run the current window scan immediately.
- `overdue_slots_today` contains `morning`: morning window was missed; run evening scan during 17:00-20:00 and avoid claiming observed morning conditions retroactively.
- `remaining_slots_today=[]`: both daily scans are complete.

Cadence guardrails:
- `--slot auto` resolves to `morning` or `evening` only inside the cadence windows.
- Duplicate morning/evening entries for the same day are rejected.
- CLI output includes cadence status (`should_scan_now`, `overdue_slots_today`, `next_slot`) so missed windows are explicit.

Log record fields:
- ts
- slot (morning|evening|setup)
- precipitation
- wind
- visibility
- surface
- action_tips (3 items)
- confidence (observed|inferred|unknown)
- notes
