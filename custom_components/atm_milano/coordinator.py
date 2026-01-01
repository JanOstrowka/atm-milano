"""DataUpdateCoordinator for ATM Milano integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ATMApiError, ATMClient
from .const import CONF_SCAN_INTERVAL, CONF_STOP_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ATMStopCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching ATM Milano stop data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance.
            entry: Config entry for this stop.
        """
        self.stop_id: str = entry.data[CONF_STOP_ID]
        self.stop_name: str | None = None
        
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.stop_id}",
            update_interval=timedelta(seconds=scan_interval),
            config_entry=entry,
        )
        
        # Use standalone client to avoid issues with Home Assistant's shared session
        # The ATM API requires specific headers that work better with a dedicated session
        self._client = ATMClient()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from ATM Milano API.

        Returns:
            Dictionary containing stop data.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        try:
            data = await self._client.async_get_stop(self.stop_id)
        except ATMApiError as err:
            raise UpdateFailed(f"Error fetching stop {self.stop_id}: {err}") from err
        
        # Store stop name for device naming
        self.stop_name = data.get("Description", f"Stop {self.stop_id}")
        
        return data

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and close the API client."""
        await super().async_shutdown()
        await self._client.async_close()

