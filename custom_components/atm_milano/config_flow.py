"""Config flow for ATM Milano integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .api import ATMApiConnectionError, ATMApiInvalidStopError, ATMClient
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_STOP_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_ID): str,
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): NumberSelector(
            NumberSelectorConfig(
                min=MIN_SCAN_INTERVAL,
                max=MAX_SCAN_INTERVAL,
                step=1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="seconds",
            )
        ),
    }
)


class ATMMilanoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ATM Milano."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step.

        Args:
            user_input: User provided configuration data.

        Returns:
            Config flow result (form or create entry).
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            stop_id = user_input[CONF_STOP_ID].strip()
            
            # Validate stop_id format (digits only, 1-10 chars)
            if not stop_id.isdigit() or len(stop_id) < 1 or len(stop_id) > 10:
                errors["base"] = "invalid_stop_id"
            else:
                # Check if already configured
                await self.async_set_unique_id(stop_id)
                self._abort_if_unique_id_configured()
                
                # Validate by fetching from API
                session = async_get_clientsession(self.hass)
                client = ATMClient(session)
                
                try:
                    data = await client.async_get_stop(stop_id)
                    stop_name = data.get("Description", f"Stop {stop_id}")
                    
                    return self.async_create_entry(
                        title=stop_name,
                        data={
                            CONF_STOP_ID: stop_id,
                            CONF_SCAN_INTERVAL: user_input.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        },
                    )
                except ATMApiInvalidStopError:
                    errors["base"] = "invalid_stop"
                except ATMApiConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error during config flow")
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

