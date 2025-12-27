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
    IN_ARRIVO = "in_arrivo"
    RICALCOLO = "ricalcolo"
    SOPPRESSA = "soppressa"
    UNKNOWN_TEXT = "unknown_text"


# Known Italian status messages (case-insensitive matching)
STATUS_IN_ARRIVO: Final = "in arrivo"
STATUS_RICALCOLO: Final = "ricalcolo"
STATUS_SOPPRESSA: Final = "soppressa"

