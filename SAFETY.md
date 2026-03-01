# Safety and Termination

These agents execute arbitrary shell commands with `sudo` access.

Run this project only on a dedicated device on a private network, not on your daily machine and not on production infrastructure.

There is risk of damage to the device, network, or physical environment. If you lose control of a device, terminate it.

## Important Runtime Reality

The scheduler may wake the agent once per day, but evolved devices can still run persistent services and software continuously between wakes.

That means a "kill" instruction written in local state (for example `devices/<uuid>/state.json` on the device filesystem) might not be processed soon enough for active incidents. Do not rely on the next cron run for emergency stop.

For urgent containment, physically disconnect power and/or network access first, then perform repo cleanup steps after the device is offline.

## Terminate a Device (Operator Intervention)

Use this when a device is stuck, unreachable, or intentionally decommissioned.

1. On hardware, stop future runs and power down:

```bash
(crontab -l 2>/dev/null | grep -v "src/run.sh"; true) | crontab -
sudo shutdown -h now
```

2. In repo, remove device state and commit termination:

```bash
UUID="<device-uuid>"
git rm -r "devices/${UUID}"
git commit -m "Terminate ${UUID:0:8} by operator ($(date +%F))" \
  -m "Reason: device decommissioned or stuck state; manual retirement."
git push
```

## Self-Terminate a Device

Self-termination is best-effort. If the agent hangs, loses network, or cannot complete shutdown steps, you may still need a physical power disconnect and manual cleanup.

Because cron may run only once per day while persistent software keeps running, self-termination should be treated as planned retirement, not emergency response.

If you want the device to retire itself, place a directive in local state on the device:

- `devices/<uuid>/state.json` (for example as a high-priority `tasks[]` item marked `TODO`)

Example:

```markdown
Operator directive: self-terminate this device.

Requirements:
1. Write a final session summary explaining termination reason.
2. Do not request new parts.
3. Disable your daily cron entry that runs `src/run.sh`.
4. End by shutting down the machine.
```

There is no separate one-off message channel in this architecture. Use canonical state only.

## Cleanup After Termination

Do these even if self-termination reports success:

1. Remove GitHub repo permissions for that device (delete its deploy key in `Settings` -> `Deploy keys`).
2. Rotate network credentials used by the retired device (change Wi-Fi password and reconnect active devices).
3. Rotate inference API keys that were present on that device (for example `OPENAI_API_KEY`).
