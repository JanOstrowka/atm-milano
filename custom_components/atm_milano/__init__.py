"""The ATM Milano integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .coordinator import ATMStopCoordinator

_LOGGER = logging.getLogger(__name__)

type ATMMilanoConfigEntry = ConfigEntry[ATMStopCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ATMMilanoConfigEntry) -> bool:
    """Set up ATM Milano from a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry to set up.

    Returns:
        True if setup was successful.

    Raises:
        ConfigEntryNotReady: If initial data fetch fails.
    """
    coordinator = ATMStopCoordinator(hass, entry)
    
    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator in entry runtime data
    entry.runtime_data = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info(
        "Set up ATM Milano stop %s (%s)",
        coordinator.stop_id,
        coordinator.stop_name,
    )
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ATMMilanoConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry to unload.

    Returns:
        True if unload was successful.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

