"""API client for ATM Milano."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# Headers to mimic browser requests (required by Akamai protection)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
    "Referer": "https://giromilano.atm.it/",
    "Origin": "https://giromilano.atm.it",
}


class ATMApiError(Exception):
    """Exception raised when API call fails."""


class ATMApiConnectionError(ATMApiError):
    """Exception raised when connection to API fails."""


class ATMApiInvalidStopError(ATMApiError):
    """Exception raised when stop ID is invalid or not found."""


class ATMClient:
    """Client to interact with ATM Milano API."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API client.

        Args:
            session: aiohttp client session for making requests.
        """
        self._session = session

    async def async_get_stop(self, stop_id: str) -> dict[str, Any]:
        """Fetch stop data from ATM Milano API.

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
        
        try:
            async with asyncio.timeout(API_TIMEOUT):
                async with self._session.get(url, headers=DEFAULT_HEADERS) as response:
                    if response.status == 404:
                        raise ATMApiInvalidStopError(
                            f"Stop ID {stop_id} not found"
                        )
                    
                    if response.status == 403:
                        raise ATMApiConnectionError(
                            "Access denied by ATM Milano API (403 Forbidden)"
                        )
                    
                    if response.status != 200:
                        raise ATMApiError(
                            f"API returned status {response.status}"
                        )
                    
                    # Check content type to detect HTML error pages
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" in content_type:
                        text = await response.text()
                        if "Access Denied" in text:
                            raise ATMApiConnectionError(
                                "Access denied by ATM Milano API (blocked by protection)"
                            )
                        raise ATMApiError(
                            "API returned HTML instead of JSON"
                        )
                    
                    data = await response.json()
                    
        except asyncio.TimeoutError as err:
            raise ATMApiConnectionError(
                f"Timeout connecting to ATM Milano API"
            ) from err
        except aiohttp.ClientError as err:
            raise ATMApiConnectionError(
                f"Error connecting to ATM Milano API: {err}"
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

