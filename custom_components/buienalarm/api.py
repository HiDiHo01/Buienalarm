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
        # self._session = session
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        async with self._session.get(self._url, timeout=self._timeout, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            _LOGGER.debug(
                "[API%s] Retrieved metadata keys: %s", self._sfx, list(data.keys())
            )
            return data

    async def async_get_nowcast(
        self,
        timeout: ClientTimeout | None = None,
    ) -> dict[str, object]:
        """Download raw JSON from Buienalarm endpoint with full debug tracing."""
        timeout = timeout or self._timeout
        _LOGGER.debug("[API%s] → GET %s (timeout=%ss)", self._sfx, self._url, timeout.total)

        # Log what headers aiohttp will send
        effective_headers = dict(self._session.headers)  # default session headers
        _LOGGER.debug("[API%s] → Effective request headers: %s", self._sfx, effective_headers)

        fetch_started_at: datetime = datetime.now(timezone.utc)

        # Define the request headers
        headers = {
            "User-Agent": "HomeAssistant/2025.10.2 aiohttp/3.13.0 Python/3.13",
            "Accept-Encoding": "gzip",
        }

        _LOGGER.debug("[API%s] → Set request headers to: %s", self._sfx, headers)
        try:
            async with async_timeout.timeout(timeout.total):
                async with self._session.get(
                    self._url,
                    timeout=timeout,
                    headers=headers,
                    #                    headers={
                    #                        "Accept-Encoding": "gzip",
                    #                        "User-Agent": f"HomeAssistant/{VERSION} {DOMAIN}",
                    #                    },
                ) as resp:
                    resp.raise_for_status()
                    headers: dict = resp.headers
                    content: dict = await resp.json()

                    age_header: int = int(headers.get("Age", "0"))
                    _LOGGER.debug("[API]   Age header: %s", age_header)
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
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        _LOGGER.debug("[API%s]   Status OK (200), processing response", self._sfx)
                        _LOGGER.debug("[API%s]   Response is expected to be JSON", self._sfx)
                        _LOGGER.debug("[API%s]   Will parse response as JSON", self._sfx)
                        _LOGGER.info(
                            "[API%s]   Successfully fetched data from Buienalarm", self._sfx
                        )
                        _LOGGER.info("[API%s]   Response received", self._sfx)
                        _LOGGER.info("[API%s]   ---------> Response data: %s", self._sfx, data)
                        return {
                            "timeseries": content,
                            "retrieval_time": fetch_started_at,
                            "cache_age": age_header,
                        }
                    if resp.status == 204:
                        return {}
                    await self._log_response_meta(resp)
                    compressed = resp.headers.get("Content-Length", "?")
                    _LOGGER.debug(
                        "[API%s]   compressed payload: %s bytes", self._sfx, compressed
                    )
                    _LOGGER.debug(
                        "[API%s]   parsed JSON → %d top-level keys",
                        self._sfx,
                        len(data) if isinstance(data, dict) else -1,
                    )
                    pretty = _dump_json(data).replace("\n", "\n    ")
                    _LOGGER.debug("[API%s]   full JSON dump:\n    %s", self._sfx, pretty)
        except asyncio.TimeoutError as err:
            _LOGGER.error("[API%s]   TIMEOUT after %ss", self._sfx, timeout.total)
            raise ApiError("Timeout while requesting Buienalarm data") from err
        except (aiohttp.ClientError, socket.gaierror) as err:
            _LOGGER.error("[API%s]   HTTP error: %s", self._sfx, err)
            raise ApiError(err) from err
        except ValueError as err:
            _LOGGER.error("[API%s]   JSON decode error: %s", self._sfx, err)
            raise ApiError("Invalid JSON") from err

        await self._maybe_dismiss_notification()
        # return cast(dict[str, object], data)

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
        _LOGGER.debug(
            "[API%s] async_get_data() completed in %s", self._sfx, result.get("retrieval_time", "unknown")
        )
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
