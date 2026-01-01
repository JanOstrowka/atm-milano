"""API client for ATM Milano."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# Headers to mimic browser requests from GiroMilano website
# These headers make the request look like it's coming from a mobile browser
# browsing the official giromilano.atm.it website
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://giromilano.atm.it/",
    "Origin": "https://giromilano.atm.it",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


class ATMApiError(Exception):
    """Exception raised when API call fails."""


class ATMApiConnectionError(ATMApiError):
    """Exception raised when connection to API fails."""


class ATMApiInvalidStopError(ATMApiError):
    """Exception raised when stop ID is invalid or not found."""


class ATMClient:
    """Client to interact with ATM Milano API."""

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        """Initialize the API client.

        Args:
            session: Optional aiohttp client session. If not provided, 
                     a new session will be created for each request.
        """
        self._session = session
        self._owns_session = False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session with proper settings."""
        if self._session is not None:
            return self._session
        
        # Create a new session with explicit settings for ATM API
        # This avoids potential issues with Home Assistant's shared session
        timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
        self._session = aiohttp.ClientSession(timeout=timeout)
        self._owns_session = True
        return self._session

    async def async_close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None
            self._owns_session = False

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
        session = await self._get_session()
        
        _LOGGER.debug("Fetching stop data from: %s", url)
        
        try:
            async with asyncio.timeout(API_TIMEOUT):
                async with session.get(
                    url, 
                    headers=DEFAULT_HEADERS,
                    ssl=True,  # Ensure SSL verification
                ) as response:
                    _LOGGER.debug(
                        "API response: status=%s, content-type=%s",
                        response.status,
                        response.headers.get("Content-Type", "unknown"),
                    )
                    
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
                        _LOGGER.debug("Received HTML response: %s...", text[:200])
                        if "Access Denied" in text or "access denied" in text.lower():
                            raise ATMApiConnectionError(
                                "Access denied by ATM Milano API (blocked by protection)"
                            )
                        raise ATMApiError(
                            "API returned HTML instead of JSON"
                        )
                    
                    data = await response.json()
                    
        except asyncio.TimeoutError as err:
            raise ATMApiConnectionError(
                "Timeout connecting to ATM Milano API"
            ) from err
        except aiohttp.ClientError as err:
            _LOGGER.debug("aiohttp ClientError: %s", err)
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

