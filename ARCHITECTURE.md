# WDIB Architecture

WDIB is split into two planes:

1. Control Plane (WDIB)
- Owns durable state (`devices/<uuid>/state.json`)
- Owns cycle orchestration (`work_order` -> `worker_result`)
- Owns hardware request lifecycle via machine-observed detection/verification
- Owns event log (`events.ndjson`), session records, and sanitized publication commit/push
- Owns modular notification routing (`src/wdib/notifications/`) for optional channels (for example Slack)

2. Worker Plane (Codex)
- Executes one scoped objective from `work_order`
- Writes one structured `worker_result` file
- Proposes new tasks/hardware requests/incidents through contract fields

## Core Principles

- No human software acknowledgment state for hardware installs.
- Hardware requests advance only by machine evidence:
  - `OPEN` -> `DETECTED` -> `VERIFIED`
  - Optional fallback: `DETECTED` -> `OPEN` if signal disappears
- GitHub remains the observability control tower; each cycle publishes only `devices/<uuid>/public/`.
- Contract-first integration: all control/worker exchange validated by JSON schema.

## Canonical Files per Device

- `devices/<uuid>/state.json`
- `devices/<uuid>/events.ndjson`
- `devices/<uuid>/sessions/day_XXX_<date>.json`
- `devices/<uuid>/runtime/work_orders/<cycle>.json`
- `devices/<uuid>/runtime/worker_results/<cycle>.json`
- `devices/<uuid>/public/status.json`
- `devices/<uuid>/public/daily/day_XXX_<date>.md`

## Tick Flow

1. Load state.
2. Probe hardware requests and transition statuses based on observed evidence.
3. Plan next objective and emit `work_order`.
4. Run Codex worker.
5. Validate and apply `worker_result` through reducer.
6. Persist state/events/session.
7. Commit and push sanitized public artifacts.
