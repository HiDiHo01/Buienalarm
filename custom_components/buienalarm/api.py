# api.py
import asyncio
import json
import logging
import socket
import uuid

import aiohttp
import async_timeout
from aiohttp import ClientSession
from homeassistant.components.persistent_notification import \
    async_create as async_create_notification
from homeassistant.components.persistent_notification import \
    async_dismiss as async_dismiss_notification
from homeassistant.core import HomeAssistant

from .const import API_ENDPOINT, API_TIMEOUT
from .exceptions import ApiError, BuienalarmApiException

_LOGGER: logging.Logger = logging.getLogger(__name__)


class BuienalarmApiClient:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        session: ClientSession,
        hass: HomeAssistant,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.session = session
        self.hass = hass
        self.notification_id = None
        _LOGGER.debug("BuienalarmApiClient initialized with provided coordinates.")

    async def old_fetch_data(self):
        """Fetch Buienalarm data."""
        _LOGGER.debug("fetch_data BuienalarmApiClient data")
        url = f"http://cdn.buienalarm.nl/api/4.0/nowcast/timeseries/{self.latitude}/{self.longitude}/"

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    _LOGGER.error("Error fetching Buienalarm data, status code: %d", response.status)
                    return

                self.data = await response.json()

        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching Buienalarm data: %s", err)

    async def async_update(self):
        """Update Buienalarm data."""
        _LOGGER.debug("async_update BuienalarmApiClient data")
        await self.fetch_data()

    async def async_get_data(self):
        """Get data from the Buienalarm API."""
        _LOGGER.debug("async_get_data BuienalarmApiClient data")
        url = API_ENDPOINT.format(self.latitude, self.longitude)
        return await self._api_wrapper(url)

    async def _api_wrapper(self, url):
        """Private method to get information from the API."""
        _LOGGER.debug("_api_wrapper BuienalarmApiClient data")
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                response = await self.session.get(url)
                _LOGGER.debug("Response status: %s", response.status)
                _LOGGER.debug("Response headers: %s", response.headers)
                response_text = await response.text()
                _LOGGER.debug("Response text: %s", response_text)

                await self._handle_error_responses(response_text)

                data = await self._parse_json_response(response, response_text)
                _LOGGER.debug("Raw JSON response: %s", data)

                if isinstance(data, dict) and "data" in data:
                    _LOGGER.debug("OK! Data is dict and ""data"" exist")
                    buienalarm_data = data["data"][0]
                    if buienalarm_data:
                        _LOGGER.debug("OK! buienalarm_data")
                        await self._handle_notification_dismissal()
                        return buienalarm_data
                    else:
                        raise ApiError("No 'buienalarm_data' data in the response")
                else:
                    raise ApiError("Invalid data type or structure in JSON response")
        except asyncio.TimeoutError as exception:
            _LOGGER.error(
                "Timeout error fetching information from %s - %s",
                url,
                exception,
            )
        except (aiohttp.ClientError, socket.gaierror) as exception:
            await self._handle_error_logging(exception, url)
        except BuienalarmApiException as exception:
            await self._handle_error_logging(exception)
            raise exception

    async def _handle_error_responses(self, response_text):
        if "De server ondervindt een probleem" in response_text:
            raise BuienalarmApiException("Error fetching information from the API")

    async def _parse_json_response(self, response, response_text):
        _LOGGER.debug("_parse_json_response BuienalarmApiClient data")
        if response.headers.get("Content-Type") != "application/json":
            raise ApiError("Invalid content type in the response")

        try:
            if response.status == 200:
                data = json.loads(response_text)
            else:
                data = None
        except json.JSONDecodeError as exception:
            _LOGGER.error(
                "Error decoding JSON response - %s: %s",
                exception,
                response_text,
            )
            raise ApiError("Invalid JSON data in the response")

        return data

    async def _handle_notification_dismissal(self):
        if self.notification_id is not None and self.notification_exists():
            await async_dismiss_notification(self.hass, self.notification_id)
            self.notification_id = None

    async def _handle_error_logging(self, exception, url=None):
        if url:
            _LOGGER.error(
                "Error fetching information from %s - %s",
                url,
                exception,
            )
        else:
            _LOGGER.error("Error: %s", exception)

    def notification_exists(self):
        notifications = self.hass.data.get("persistent_notification", {})
        if not isinstance(notifications, dict):
            return False

        existing_notification = notifications.get(self.notification_id)

        if existing_notification is not None:
            _LOGGER.debug("Notification exists: %s", self.notification_id)
            return True

        _LOGGER.debug("Notification does not exist: %s", self.notification_id)
        return False

    async def async_fetch_daily_forecast_data(self):
        _LOGGER.debug("async_fetch_daily_forecast_data BuienalarmApiClient data")
        try:
            url = API_ENDPOINT.format(self.latitude, self.longitude)
            _LOGGER.debug("8latitude = %s, longitude = %s", self.latitude, self.longitude)
            async with async_timeout.timeout(API_TIMEOUT):
                response = await self.session.get(url)
                response.raise_for_status()
                response_text = await response.text()
                data = await self._parse_json_response(response, response_text)

                if not data is None:
                    return data.get("data", [])

        except aiohttp.ClientError as e:
            raise BuienalarmApiException(f"Error fetching daily forecast data: {e}")
