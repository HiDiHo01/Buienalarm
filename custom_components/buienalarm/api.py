"""Async API client used by the Buienalarm Home Assistant integration."""

import asyncio
import json
import logging
import random
import socket
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Final, cast

import aiohttp
from aiohttp import ClientResponse, ClientSession, ClientTimeout
from homeassistant.components.persistent_notification import (
    async_dismiss as hass_async_dismiss_notification,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_ENDPOINT, API_TIMEOUT
from .exceptions import ApiError

_LOGGER = logging.getLogger(__name__)

_USER_AGENT_LIST: Final[list[str]] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18363",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
]


def _get_random_user_agent() -> str:
    """Return a random user agent from the list."""
    return random.choice(_USER_AGENT_LIST)


_DEF_DUMP_OPTS: dict[str, object] = {
    "ensure_ascii": False,
    "allow_nan": False,
    "indent": 2,
    "sort_keys": True,
}


def _dump_json(data: object) -> str:
    """Safely serialize data to a JSON-formatted string."""
    try:
        return json.dumps(data, **_DEF_DUMP_OPTS)
    except (TypeError, ValueError) as err:
        _LOGGER.debug("Failed to serialize JSON: %s", err)
        return repr(data)


def _safe_headers_dict(headers_obj: object) -> dict[str, str]:
    """Safely extract headers dict from object (handling Mocks/non-mappings)."""
    if headers_obj is None:
        return {}
    if isinstance(headers_obj, Mapping):
        return {str(k): str(v) for k, v in headers_obj.items()}
    try:
        if hasattr(headers_obj, "items") and callable(headers_obj.items):
            items = headers_obj.items()
            if isinstance(items, Mapping):
                return {str(k): str(v) for k, v in items.items()}
            return {str(k): str(v) for k, v in items}
        return dict(headers_obj)
    except Exception:
        return {}


class BuienalarmApiClient:
    """Async wrapper around Buienalarm's JSON timeseries endpoint."""

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
        """Initialize the API client."""
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

        _LOGGER.debug("[API%s] Initialized BuienalarmApiClient", self._sfx)

    @property
    def base_url(self) -> str:
        """Return the formatted base URL."""
        return self._url

    async def async_get_initial_data(self) -> dict[str, object]:
        """Fetch initial metadata once."""
        _LOGGER.debug("[API%s] Fetching initial metadata", self._sfx)
        user_agent = _get_random_user_agent()
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.buienalarm.nl/",
            "Origin": "https://www.buienalarm.nl",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

        try:
            async with self._session.get(
                self._url, timeout=self._timeout, headers=headers
            ) as resp:
                _LOGGER.debug(
                    "[API%s] Initial data response status: %s", self._sfx, resp.status
                )
                resp.raise_for_status()
                data = await resp.json()
                if isinstance(data, dict):
                    _LOGGER.debug(
                        "[API%s] Retrieved metadata keys: %s",
                        self._sfx,
                        list(data.keys()),
                    )
                return data if isinstance(data, dict) else {"data": data}
        except aiohttp.ClientResponseError as err:
            _LOGGER.error(
                "[API%s] HTTP error fetching initial data: %s", self._sfx, err
            )
            raise

    async def async_get_nowcast(
        self,
        timeout: ClientTimeout | None = None,
    ) -> dict[str, object]:
        """Download raw JSON from Buienalarm endpoint."""
        timeout = timeout or self._timeout
        timeout_seconds = timeout.total if timeout.total is not None else API_TIMEOUT
        _LOGGER.debug(
            "[API%s] → GET %s (timeout=%ss)", self._sfx, self._url, timeout_seconds
        )

        fetch_started_at: datetime = datetime.now(timezone.utc)

        user_agent = _get_random_user_agent()
        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.buienalarm.nl/",
            "Origin": "https://www.buienalarm.nl",
            "DNT": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

        try:
            async with asyncio.timeout(timeout_seconds):
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

                    resp_headers = _safe_headers_dict(getattr(resp, "headers", None))
                    age_header: int = 0
                    if "Age" in resp_headers:
                        try:
                            age_header = int(resp_headers["Age"])
                        except ValueError:
                            pass

                    data = await resp.json(content_type=None)

                    if isinstance(data, dict):
                        result = dict(data)
                        result.setdefault("retrieval_time", fetch_started_at)
                        result.setdefault("cache_age", age_header)
                        await self._maybe_dismiss_notification()
                        return result

                    await self._maybe_dismiss_notification()
                    return {
                        "timeseries": data,
                        "data": data if isinstance(data, list) else [],
                        "retrieval_time": fetch_started_at,
                        "cache_age": age_header,
                    }

        except TimeoutError as err:
            _LOGGER.error("[API%s] TIMEOUT after %ss", self._sfx, timeout_seconds)
            raise ApiError("Timeout while requesting Buienalarm data") from err
        except (aiohttp.ClientError, socket.gaierror) as err:
            _LOGGER.error("[API%s] HTTP error: %s", self._sfx, err)
            raise ApiError(str(err)) from err
        except ValueError as err:
            _LOGGER.error("[API%s] JSON decode error: %s", self._sfx, err)
            raise ApiError("Invalid JSON") from err

    async def async_get_data(
        self,
        timeout: ClientTimeout | None = None,
    ) -> dict[str, Any]:
        """Fetch latest data from Buienalarm API."""
        return await self.async_get_nowcast(timeout=timeout)

    async def _maybe_dismiss_notification(self) -> None:
        """Dismiss persistent notification if displayed."""
        if self._notification_id and self._notification_exists():
            await hass_async_dismiss_notification(self._hass, self._notification_id)
            self._notification_id = None

    def _notification_exists(self) -> bool:
        """Check if persistent notification exists."""
        pn_data = self._hass.data.get("persistent_notification")
        return isinstance(pn_data, dict) and self._notification_id in pn_data

    @property
    def _sfx(self) -> str:
        """Return log prefix suffix."""
        return f" id={self._entry_id}" if self._entry_id else ""
