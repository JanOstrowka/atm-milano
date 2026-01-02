"""Sensor platform for ATM Milano integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ATMMilanoConfigEntry
from .const import (
    CONF_STOP_ID,
    DOMAIN,
    STATUS_IN_ARRIVO,
    STATUS_RICALCOLO,
    STATUS_SOPPRESSA,
    WAIT_MINUTES_PATTERN,
    WaitStatus,
)
from .coordinator import ATMStopCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class ParsedWaitMessage:
    """Parsed wait message data."""

    raw_text: str
    state_value: int | str
    wait_minutes: int | None
    status: WaitStatus
    unit: str | None


def parse_wait_message(wait_msg: str | None) -> ParsedWaitMessage:
    """Parse a WaitMessage from the API response.

    Args:
        wait_msg: The WaitMessage string from the API.

    Returns:
        ParsedWaitMessage with extracted data.
    """
    if wait_msg is None:
        return ParsedWaitMessage(
            raw_text="",
            state_value="unknown",
            wait_minutes=None,
            status=WaitStatus.UNKNOWN_TEXT,
            unit=None,
        )

    raw_text = wait_msg.strip()
    lower_text = raw_text.lower()

    # Check for numeric minutes pattern (e.g., "2 min", "15 min")
    match = WAIT_MINUTES_PATTERN.match(raw_text)
    if match:
        minutes = int(match.group(1))
        return ParsedWaitMessage(
            raw_text=raw_text,
            state_value=minutes,
            wait_minutes=minutes,
            status=WaitStatus.MINUTES,
            unit="min",
        )

    # Check for "in arrivo" (arriving)
    if lower_text == STATUS_IN_ARRIVO:
        return ParsedWaitMessage(
            raw_text=raw_text,
            state_value=raw_text,  # Preserve original capitalization
            wait_minutes=0,
            status=WaitStatus.IN_ARRIVO,
            unit=None,
        )

    # Check for "ricalcolo" (recalculating)
    if lower_text == STATUS_RICALCOLO:
        return ParsedWaitMessage(
            raw_text=raw_text,
            state_value=raw_text,
            wait_minutes=None,
            status=WaitStatus.RICALCOLO,
            unit=None,
        )

    # Check for "Soppressa" (cancelled)
    if lower_text == STATUS_SOPPRESSA:
        return ParsedWaitMessage(
            raw_text=raw_text,
            state_value=raw_text,
            wait_minutes=None,
            status=WaitStatus.SOPPRESSA,
            unit=None,
        )

    # Unknown text - pass through
    return ParsedWaitMessage(
        raw_text=raw_text,
        state_value=raw_text,
        wait_minutes=None,
        status=WaitStatus.UNKNOWN_TEXT,
        unit=None,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ATMMilanoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ATM Milano sensors from a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.
        async_add_entities: Callback to add entities.
    """
    coordinator = entry.runtime_data
    stop_id = entry.data[CONF_STOP_ID]

    entities: list[ATMLineSensor] = []
    
    # Track which line+direction combinations we've seen
    seen_keys: set[str] = set()

    if coordinator.data and "Lines" in coordinator.data:
        for line in coordinator.data["Lines"]:
            # Line info is nested under "Line" object
            line_info = line.get("Line", {})
            line_code = line_info.get("LineCode", "")
            # Direction is at top level and comes as a string from the API
            direction = str(line.get("Direction", "0"))
            entity_key = f"{line_code}_{direction}"

            if entity_key in seen_keys:
                continue
            seen_keys.add(entity_key)

            entities.append(
                ATMLineSensor(
                    coordinator=coordinator,
                    stop_id=stop_id,
                    line_code=line_code,
                    direction=direction,
                    line_description=line_info.get("LineDescription", ""),
                    transport_mode=line_info.get("TransportMode"),
                )
            )

    async_add_entities(entities)
    _LOGGER.debug("Added %d sensors for stop %s", len(entities), stop_id)


class ATMLineSensor(CoordinatorEntity[ATMStopCoordinator], SensorEntity):
    """Sensor for an ATM Milano line at a stop."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ATMStopCoordinator,
        stop_id: str,
        line_code: str,
        direction: str,
        line_description: str,
        transport_mode: int | None,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: Data update coordinator.
            stop_id: Stop ID.
            line_code: Line code (e.g., "2", "92").
            direction: Direction as string ("0" or "1").
            line_description: Line description (e.g., "P.za Bausan - P.le Negrelli").
            transport_mode: Transport mode number.
        """
        super().__init__(coordinator)

        self._stop_id = stop_id
        self._line_code = line_code
        self._direction = direction
        self._line_description = line_description
        self._transport_mode = transport_mode

        # Unique ID for this sensor
        self._attr_unique_id = f"{stop_id}_{line_code}_{direction}"

        # Entity name
        if line_description:
            self._attr_name = f"{line_code} – {line_description}"
        else:
            self._attr_name = line_code

        # Device info - group all sensors under the stop device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, stop_id)},
            name=coordinator.stop_name or f"Stop {stop_id}",
            manufacturer="ATM Milano",
            model="Surface Stop",
        )

        # Parse initial state
        self._parsed: ParsedWaitMessage | None = None
        self._update_parsed_state()

    def _find_line_data(self) -> dict[str, Any] | None:
        """Find this line's data in the coordinator data.

        Returns:
            Line data dictionary or None if not found.
        """
        if not self.coordinator.data or "Lines" not in self.coordinator.data:
            return None

        for line in self.coordinator.data["Lines"]:
            # Line info is nested under "Line" object
            line_info = line.get("Line", {})
            # Direction is at top level and is a string
            if (
                line_info.get("LineCode") == self._line_code
                and str(line.get("Direction", "")) == self._direction
            ):
                return line

        return None

    def _update_parsed_state(self) -> None:
        """Update the parsed state from coordinator data."""
        line_data = self._find_line_data()
        if line_data:
            wait_msg = line_data.get("WaitMessage")
            self._parsed = parse_wait_message(wait_msg)
        else:
            self._parsed = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_parsed_state()
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> int | str | None:
        """Return the state of the sensor."""
        if self._parsed is None:
            return None
        return self._parsed.state_value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if self._parsed is None:
            return None
        return self._parsed.unit

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        # Also check if this specific line exists in the data
        return self._find_line_data() is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {
            "line_code": self._line_code,
            "line_description": self._line_description,
        }

        if self._parsed:
            attrs["wait_text"] = self._parsed.raw_text
            attrs["wait_minutes"] = self._parsed.wait_minutes
            attrs["status"] = self._parsed.status.value

        return attrs

