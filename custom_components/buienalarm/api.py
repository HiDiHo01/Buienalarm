# api.py – Buienalarm API client with ultra‑verbose debug logging
"""Async API client used by the Buienalarm Home‑Assistant integration.

Every network hop, JSON parse and exceptional path is traced with
`_LOGGER.debug()` or `_LOGGER.error()`.  The log messages are designed so
that you can reconstruct an entire request/response life‑cycle by simply
filtering on the `[API]` tag.
"""

import asyncio
import json
import logging
import random
import socket
from datetime import datetime, timezone
from typing import Any, Final, cast

import aiohttp
import async_timeout
from aiohttp import ClientResponse, ClientSession, ClientTimeout
from homeassistant.components.persistent_notification import (
    async_dismiss as hass_async_dismiss_notification,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_ENDPOINT, API_TIMEOUT
from .exceptions import ApiError

# -----------------------------------------------------------------------------
#  Logger setup
# -----------------------------------------------------------------------------
_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
#  User Agent rotation to avoid 403 errors
# -----------------------------------------------------------------------------
_USER_AGENT_LIST: Final[list[str]] = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
]


def _get_random_user_agent() -> str:
    """Return a random user agent from the list."""
    return random.choice(_USER_AGENT_LIST)


# -----------------------------------------------------------------------------
#  JSON pretty print helper
# -----------------------------------------------------------------------------
_DEF_DUMP_OPTS: dict[str, object] = {
    "ensure_ascii": False,
    "allow_nan": False,
    "indent": 2,
    "sort_keys": True,
}


def _dump_json(data: object) -> str:
    """Safely serialize data to a JSON-formatted string.

    Falls back to `repr(data)` if serialization fails.
    """
    try:
        return json.dumps(data, **_DEF_DUMP_OPTS)
    except (TypeError, ValueError) as err:
        _LOGGER.debug("Failed to serialize JSON: %s", err)
        return repr(data)

# -----------------------------------------------------------------------------
#  API Client
# -----------------------------------------------------------------------------


class BuienalarmApiClient:
    """Async wrapper around Buienalarm's JSON timeseries endpoint with verbose logging."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        session: ClientSession | None,
        hass: HomeAssistant,
        entry_id: str | None = None,
        *,
        timeout: int = API_TIMEOUT,
    ) -> None:
        self.latitude: Final[float] = cast(float, latitude)
        self.longitude: Final[float] = cast(float, longitude)
        self._session: Final[ClientSession] = (
            session if session else async_get_clientsession(hass)
        )
        self._hass: Final[HomeAssistant] = hass
        self._entry_id: Final[str | None] = entry_id
        self._url: Final[str] = API_ENDPOINT.format(self.latitude, self.longitude)
        self._timeout: Final[ClientTimeout] = ClientTimeout(total=timeout)
        self._notification_id: str | None = None

        # Verbose diagnostics
        _LOGGER.debug("[API%s] Initialized BuienalarmApiClient", self._sfx)
        _LOGGER.debug("[API%s] Latitude: %s", self._sfx, self.latitude)
        _LOGGER.debug("[API%s] Longitude: %s", self._sfx, self.longitude)
        _LOGGER.debug("[API%s] Formatted URL: %s", self._sfx, self._url)
        _LOGGER.debug("[API%s] Timeout: %ss", self._sfx, self._timeout.total)
        _LOGGER.debug("[API%s] Entry ID: %s", self._sfx, self._entry_id or "N/A")
        _LOGGER.debug(
            "[API%s] Session: %s (%s)",
            self._sfx,
            "provided externally" if session else "created via async_get_clientsession()",
            type(self._session).__name__,
        )
        _LOGGER.debug("[API%s] Notification ID initialized as None", self._sfx)

    @property
    def base_url(self) -> str:
        return API_ENDPOINT.format(self.latitude, self.longitude)

    async def async_get_initial_data(self) -> dict[str, object]:
        """
        Fetch static metadata (e.g., station name, available keys) once.
        """
        _LOGGER.debug("[API%s] Fetching initial metadata", self._sfx)
        user_agent = _get_random_user_agent()
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.buienalarm.nl/",
            "Origin": "https://www.buienalarm.nl",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }
        _LOGGER.debug("[API%s] Using User-Agent: %s", self._sfx, user_agent)
        
        try:
            async with self._session.get(self._url, timeout=self._timeout, headers=headers) as resp:
                _LOGGER.debug("[API%s] Initial data response status: %s", self._sfx, resp.status)
                resp.raise_for_status()
                data = await resp.json()
                _LOGGER.debug(
                    "[API%s] Retrieved metadata keys: %s", self._sfx, list(data.keys())
                )
                return data
        except aiohttp.ClientResponseError as err:
            _LOGGER.error("[API%s] HTTP error fetching initial data: %s", self._sfx, err)
            _LOGGER.error("[API%s] Response headers: %s", self._sfx, dict(err.headers) if err.headers else "N/A")
            raise

    async def async_get_nowcast(
        self,
        timeout: ClientTimeout | None = None,
    ) -> dict[str, object]:
        """Download raw JSON from Buienalarm endpoint with full debug tracing."""
        timeout = timeout or self._timeout
        _LOGGER.debug("[API%s] → GET %s (timeout=%ss)", self._sfx, self._url, timeout.total)

        fetch_started_at: datetime = datetime.now(timezone.utc)

        # Get random user agent to avoid 403 errors
        user_agent = _get_random_user_agent()
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.buienalarm.nl/",
            "Origin": "https://www.buienalarm.nl",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

        _LOGGER.debug("[API%s] → Using User-Agent: %s", self._sfx, user_agent)
        _LOGGER.debug("[API%s] → Request headers: %s", self._sfx, headers)

        try:
            async with async_timeout.timeout(timeout.total):
                async with self._session.get(
                    self._url,
                    timeout=timeout,
                    headers=headers,
                ) as resp:
                    _LOGGER.debug("[API%s]   HTTP %s", self._sfx, resp.status)
                    
                    if resp.status != 200:
                        _LOGGER.error(
                            "[API%s]   HTTP error: %s %s",
                            self._sfx,
                            resp.status,
                            resp.reason,
                        )
                        raise ApiError(f"HTTP error {resp.status}: {resp.reason}")
                    
                    _LOGGER.debug("[API%s]   Response received", self._sfx)
                    _LOGGER.debug("[API%s]   Response headers: %s", self._sfx, dict(resp.headers))
                    _LOGGER.debug("[API%s]   Response content type: %s", self._sfx,
                                resp.headers.get("Content-Type", "unknown"))
                    _LOGGER.debug("[API%s]   Response content length: %s",
                                self._sfx, resp.headers.get("Content-Length", "?"))
                    
                    # Parse JSON response
                    data = await resp.json(content_type=None)
                    age_header: int = int(resp.headers.get("Age", "0"))
                    
                    _LOGGER.debug("[API%s]   Cache Age header: %s", self._sfx, age_header)
                    _LOGGER.debug("[API%s]   Status OK (200), processing response", self._sfx)
                    _LOGGER.debug(
                        "[API%s]   Parsed JSON → %d top-level keys",
                        self._sfx,
                        len(data) if isinstance(data, dict) else -1,
                    )
                    
                    pretty = _dump_json(data).replace("\n", "\n    ")
                    _LOGGER.debug("[API%s]   Full JSON dump:\n    %s", self._sfx, pretty)
                    
                    _LOGGER.info(
                        "[API%s]   Successfully fetched data from Buienalarm", self._sfx
                    )
                    
                    await self._maybe_dismiss_notification()
                    
                    return {
                        "timeseries": data,
                        "retrieval_time": fetch_started_at,
                        "cache_age": age_header,
                    }
                    
        except asyncio.TimeoutError as err:
            _LOGGER.error("[API%s]   TIMEOUT after %ss", self._sfx, timeout.total)
            raise ApiError("Timeout while requesting Buienalarm data") from err
        except (aiohttp.ClientError, socket.gaierror) as err:
            _LOGGER.error("[API%s]   HTTP error: %s", self._sfx, err)
            raise ApiError(str(err)) from err
        except ValueError as err:
            _LOGGER.error("[API%s]   JSON decode error: %s", self._sfx, err)
            raise ApiError("Invalid JSON") from err

    async def async_get_data(
        self,
        timeout: ClientTimeout | None = None,
    ) -> dict[str, Any]:
        """Alias for async_get_nowcast with extra tracing."""
        _LOGGER.debug("[API%s] async_get_data() called with timeout: %s", self._sfx, timeout)
        if timeout is None:
            timeout = self._timeout
            _LOGGER.debug("[API%s] No timeout provided, using default: %ss", self._sfx, timeout.total)
        else:
            _LOGGER.debug("[API%s] Using provided timeout: %ss", self._sfx, timeout.total)
        
        result = await self.async_get_nowcast(timeout=timeout)
        
        _LOGGER.debug("[API%s] async_get_data → result type: %s", self._sfx, type(result).__name__)
        if isinstance(result, dict):
            _LOGGER.debug("[API%s] async_get_data → result keys: %s", self._sfx, list(result.keys()))
        _LOGGER.debug(
            "[API%s] async_get_data → returning %d top-level keys",
            self._sfx,
            len(result) if isinstance(result, dict) else -1,
        )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _log_response_meta(self, resp: ClientResponse) -> None:
        _LOGGER.debug(
            "[API%s]   HTTP %s • %sB • hdr-ct=%s",
            self._sfx,
            resp.status,
            resp.headers.get("Content-Length", "?"),
            resp.headers.get("Content-Type"),
        )
        _LOGGER.debug("[API%s]   Resp-Headers: %s", self._sfx, dict(resp.headers))

    async def _maybe_dismiss_notification(self) -> None:
        if self._notification_id and self._notification_exists():
            await hass_async_dismiss_notification(self._hass, self._notification_id)
            _LOGGER.debug("[API%s] dismissed notification %s", self._sfx, self._notification_id)
            self._notification_id = None

    def _notification_exists(self) -> bool:
        return (
            isinstance(self._hass.data.get("persistent_notification"), dict)
            and self._notification_id in self._hass.data["persistent_notification"]
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def _sfx(self) -> str:
        """Return a short suffix for logs/notifications: '' or f'‑{entry_id}'."""
        return f" id={self._entry_id}" if self._entry_id else ""
        return f" id={self._entry_id}" if self._entry_id else ""
