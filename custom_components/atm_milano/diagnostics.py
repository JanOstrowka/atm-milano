"""Diagnostics support for ATM Milano integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import ATMMilanoConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ATMMilanoConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.

    Returns:
        Dictionary containing diagnostic data.
    """
    coordinator = entry.runtime_data

    return {
        "config_entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": dict(entry.data),
        },
        "coordinator": {
            "stop_id": coordinator.stop_id,
            "stop_name": coordinator.stop_name,
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
        },
        "api_data": coordinator.data,
    }

