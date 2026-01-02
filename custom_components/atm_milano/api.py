"""API client for ATM Milano."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from curl_cffi import requests as curl_requests
from curl_cffi.requests.exceptions import RequestException

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# Headers to mimic browser requests from GiroMilano website
DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Referer": "https://giromilano.atm.it/",
    "Origin": "https://giromilano.atm.it",
}

# Thread pool for running sync curl_cffi requests
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="atm_api")


class ATMApiError(Exception):
    """Exception raised when API call fails."""


class ATMApiConnectionError(ATMApiError):
    """Exception raised when connection to API fails."""


class ATMApiInvalidStopError(ATMApiError):
    """Exception raised when stop ID is invalid or not found."""


def _sync_get_stop(url: str) -> dict[str, Any]:
    """Synchronous function to fetch stop data using curl_cffi.
    
    Uses browser impersonation to bypass Akamai protection.
    
    Args:
        url: The API URL to fetch.
        
    Returns:
        Dictionary containing stop data.
        
    Raises:
        ATMApiConnectionError: If connection fails.
        ATMApiInvalidStopError: If stop not found.
        ATMApiError: For other API errors.
    """
    try:
        response = curl_requests.get(
            url,
            headers=DEFAULT_HEADERS,
            impersonate="chrome",  # Use Chrome browser impersonation
            timeout=API_TIMEOUT,
        )
    except RequestException as err:
        raise ATMApiConnectionError(
            f"Error connecting to ATM Milano API: {err}"
        ) from err
    
    if response.status_code == 404:
        raise ATMApiInvalidStopError("Stop not found")
    
    if response.status_code == 403:
        raise ATMApiConnectionError(
            "Access denied by ATM Milano API (403 Forbidden)"
        )
    
    if response.status_code != 200:
        raise ATMApiError(f"API returned status {response.status_code}")
    
    # Check content type to detect HTML error pages
    content_type = response.headers.get("Content-Type", "")
    if "text/html" in content_type:
        text = response.text
        if "Access Denied" in text or "access denied" in text.lower():
            raise ATMApiConnectionError(
                "Access denied by ATM Milano API (blocked by protection)"
            )
        raise ATMApiError("API returned HTML instead of JSON")
    
    try:
        data = response.json()
    except Exception as err:
        raise ATMApiError(f"Failed to parse JSON response: {err}") from err
    
    return data


class ATMClient:
    """Client to interact with ATM Milano API."""

    def __init__(self) -> None:
        """Initialize the API client."""
        pass

    async def async_close(self) -> None:
        """Close the client (no-op for curl_cffi)."""
        pass

    async def async_get_stop(self, stop_id: str) -> dict[str, Any]:
        """Fetch stop data from ATM Milano API.

        Uses curl_cffi with browser impersonation to bypass Akamai protection.

        Args:
            stop_id: The stop ID to fetch data for.

        Returns:
            Dictionary containing stop data with Description and Lines.

        Raises:
            ATMApiConnectionError: If connection fails or times out.
            ATMApiInvalidStopError: If stop ID is not found (404).
            ATMApiError: For other API errors.
        """
        url = API_BASE_URL.format(stop_id=stop_id)
        
        _LOGGER.debug("Fetching stop data from: %s", url)
        
        loop = asyncio.get_event_loop()
        
        try:
            data = await loop.run_in_executor(_executor, _sync_get_stop, url)
        except asyncio.TimeoutError as err:
            raise ATMApiConnectionError(
                "Timeout connecting to ATM Milano API"
            ) from err
        
        # Validate required fields
        if not isinstance(data, dict):
            raise ATMApiError("Invalid response format: expected dictionary")
        
        if "Description" not in data:
            raise ATMApiError("Invalid response: missing 'Description' field")
        
        if "Lines" not in data:
            raise ATMApiError("Invalid response: missing 'Lines' field")
        
        _LOGGER.debug(
            "Fetched data for stop %s (%s): %d lines",
            stop_id,
            data.get("Description"),
            len(data.get("Lines", [])),
        )
        
        return data
