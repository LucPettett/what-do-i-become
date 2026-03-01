"""Notification router for pluggable WDIB communication channels."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from ..adapters import slack_webhook


@dataclass(frozen=True)
class NotificationProvider:
    name: str
    is_configured: Callable[[], bool]
    notify_cycle: Callable[[dict[str, Any], dict[str, Any], str], dict[str, Any]]
    notify_failure: Callable[[str, str, int, datetime], dict[str, Any]]


_PROVIDERS: dict[str, NotificationProvider] = {
    "slack": NotificationProvider(
        name="slack",
        is_configured=slack_webhook.is_configured,
        notify_cycle=slack_webhook.notify_cycle_summary,
        notify_failure=slack_webhook.notify_cycle_failure,
    )
}


def _configured_channel_names() -> list[str]:
    raw = str(os.environ.get("WDIB_NOTIFICATION_CHANNELS") or "").strip()
    if not raw:
        return []
    names: list[str] = []
    for part in raw.split(","):
        name = part.strip().lower()
        if name and name not in names:
            names.append(name)
    return names


def send_cycle_notifications(
    *,
    status_payload: dict[str, Any],
    git_info: dict[str, Any],
    run_date: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for channel in _configured_channel_names():
        provider = _PROVIDERS.get(channel)
        if provider is None:
            results.append(
                {
                    "channel": channel,
                    "sent": False,
                    "reason": "channel is not registered",
                }
            )
            continue
        if not provider.is_configured():
            results.append(
                {
                    "channel": provider.name,
                    "sent": False,
                    "reason": "channel is not configured",
                }
            )
            continue
        try:
            result = provider.notify_cycle(status_payload, git_info, run_date)
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "channel": provider.name,
                    "sent": False,
                    "reason": f"channel notify failed: {exc}",
                }
            )
            continue
        result["channel"] = provider.name
        results.append(result)
    return results


def send_failure_notifications(
    *,
    device_id: str,
    cycle_id: str,
    day: int,
    ts: datetime,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for channel in _configured_channel_names():
        provider = _PROVIDERS.get(channel)
        if provider is None:
            results.append(
                {
                    "channel": channel,
                    "sent": False,
                    "reason": "channel is not registered",
                }
            )
            continue
        if not provider.is_configured():
            results.append(
                {
                    "channel": provider.name,
                    "sent": False,
                    "reason": "channel is not configured",
                }
            )
            continue
        try:
            result = provider.notify_failure(device_id, cycle_id, day, ts)
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "channel": provider.name,
                    "sent": False,
                    "reason": f"channel notify failed: {exc}",
                }
            )
            continue
        result["channel"] = provider.name
        results.append(result)
    return results
