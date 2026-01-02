"""Constants for the ATM Milano integration."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Final

DOMAIN: Final = "atm_milano"
PLATFORMS: Final = ["sensor"]

# Configuration keys
CONF_STOP_ID: Final = "stop_id"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Scan interval settings (seconds)
DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 15
MAX_SCAN_INTERVAL: Final = 120

# API settings
API_BASE_URL: Final = "https://giromilano.atm.it/proxy.tpportal/api/tpPortal/geodata/pois/stops/{stop_id}"
API_TIMEOUT: Final = 20

# Regex pattern to extract minutes from WaitMessage like "2 min", "15 min"
WAIT_MINUTES_PATTERN: Final = re.compile(r"^\s*(\d+)\s*min", re.IGNORECASE)


class WaitStatus(StrEnum):
    """Status values for wait message parsing."""

    MINUTES = "minutes"
    ARRIVING = "arriving"
    UPDATING = "updating"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


# Known Italian status messages (case-insensitive matching)
STATUS_IN_ARRIVO: Final = "in arrivo"
STATUS_RICALCOLO: Final = "ricalcolo"
STATUS_SOPPRESSA: Final = "soppressa"

# Transport types
class TransportType(StrEnum):
    """Transport type categories."""

    BUS = "bus"
    TRAM = "tram"
    METRO = "metro"
    TROLLEYBUS = "trolleybus"
    RADIOBUS = "radiobus"
    UNKNOWN = "unknown"


# Line to transport type mapping
# Based on ATM Milano line data
LINE_TYPES: Final[dict[str, TransportType]] = {
    # Metro lines
    "M1": TransportType.METRO,
    "M2": TransportType.METRO,
    "M3": TransportType.METRO,
    "M4": TransportType.METRO,
    "M5": TransportType.METRO,
    "ML": TransportType.METRO,
    # Tram lines
    "1": TransportType.TRAM,
    "2": TransportType.TRAM,
    "3": TransportType.TRAM,
    "4": TransportType.TRAM,
    "5": TransportType.TRAM,
    "7": TransportType.TRAM,
    "9": TransportType.TRAM,
    "10": TransportType.TRAM,
    "12": TransportType.TRAM,
    "14": TransportType.TRAM,
    "15": TransportType.TRAM,
    "16": TransportType.TRAM,
    "19": TransportType.TRAM,
    "23": TransportType.TRAM,
    "24": TransportType.TRAM,
    "27": TransportType.TRAM,
    "28": TransportType.TRAM,
    "29": TransportType.TRAM,
    "30": TransportType.TRAM,
    "31": TransportType.TRAM,
    "33": TransportType.TRAM,
    # Trolleybus (filobus) lines
    "90": TransportType.TROLLEYBUS,
    "91": TransportType.TROLLEYBUS,
    "92": TransportType.TROLLEYBUS,
}

# Icons for each transport type
TRANSPORT_ICONS: Final[dict[TransportType, str]] = {
    TransportType.BUS: "mdi:bus",
    TransportType.TRAM: "mdi:tram",
    TransportType.METRO: "mdi:subway",
    TransportType.TROLLEYBUS: "mdi:bus-electric",
    TransportType.RADIOBUS: "mdi:bus-school",
    TransportType.UNKNOWN: "mdi:bus",
}

# Bus icons for different statuses (only bus has variants)
BUS_STATUS_ICONS: Final[dict[WaitStatus, str]] = {
    WaitStatus.MINUTES: "mdi:bus",
    WaitStatus.ARRIVING: "mdi:bus-stop",
    WaitStatus.UPDATING: "mdi:bus-clock",
    WaitStatus.CANCELLED: "mdi:bus-alert",
    WaitStatus.UNKNOWN: "mdi:bus",
}

