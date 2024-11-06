# coordinator.py
import asyncio
import logging
from datetime import timedelta
from typing import Any, Callable

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)

from .api import BuienalarmApiClient
from .const import API_ENDPOINT, API_TIMEOUT, DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__name__)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)

_LOGGER.debug("coordinator loaded")


class BuienalarmDataUpdateCoordinator(DataUpdateCoordinator):
    _LOGGER.debug(f"coordinator: BuienalarmDataUpdateCoordinator")
    """Class to manage fetching data from the API."""
    options: dict = None

    def __init__(
        self,
        hass: HomeAssistant,
        client: BuienalarmApiClient,
        device_info: DeviceInfo,
        config_entry: ConfigEntry,
    ) -> None:

        # Initialize coordinator attributes
        self.hass = hass
        #self.latitude = latitude
        #self.longitude = longitude
        #_LOGGER.debug("cor_latitude = %s, longitude = %s", latitude, longitude)
        #self.url = API_ENDPOINT.format(latitude, longitude)
        #_LOGGER.debug("url = %s", self.url)

        self.api = client
        #self.client_session = ClientSession()
        #self.update_interval = update_interval
        # self.data = {}
        # self.refresh_task = None
        self.device_info = device_info
        self.config_entry = config_entry
        self.entities = []  # Create an empty list to store associated entities
        self.last_update_success = False

        super().__init__(
            hass=hass, logger=_LOGGER, name=DOMAIN
        )

    def get_entities(self):
        return self.entities

    async def async_add_listener(self, listener, update_supported=True):
        # Implement the logic to add a listener here
        # This method allows entities to register themselves as listeners to receive updates
        pass

    async def fetch_data(self):
        """Fetch data from the Buienalarm API asynchronously."""
        _LOGGER.debug("Fetching data")
        try:
            async with self.client_session.get(self.url) as response:
                response.raise_for_status()
                self.data = await response.json()
                self.last_update_success = True
        except (ClientResponseError, asyncio.TimeoutError) as error:
            _LOGGER.error(f"Error fetching data: {error}")
            self.last_update_success = False
            raise UpdateFailed(f"Error fetching data: {error}") from error

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Buienalarm API asynchronously."""
        _LOGGER.debug("coordinator: _async_update_data")
        _LOGGER.debug(f"Type of client_session: {type(self.api)}")
        #_LOGGER.debug(f"URL: {self.url}")
        try:
            _LOGGER.debug("coor Fetching data from API...")
            data = await self.api.async_get_data()
            # Use WeatherData to parse the data
            # self.data = data
            # await self.async_request_refresh()
            return data
        except (ClientResponseError, asyncio.TimeoutError) as error:
            _LOGGER.error(f"Error fetching Buienalarm data: {error}")
            raise UpdateFailed(error)

    async def refresh_data(self):
        """Refresh data with the specified update interval asynchronously."""
        while True:
            await self.fetch_data()
            await asyncio.sleep(self.update_interval.total_seconds())

    def get_value(
        self, key: str, convert_to: Callable = str
    ) -> float | int | str | None:
        """Get a value from the retrieved data and convert to given type"""
        if key in self.data:
            try:
                return convert_to(self.data.get(key, None))
            except ValueError:
                _LOGGER.warning("Value %s with key %s can't be converted to %s", self.data.get(key, None), key, convert_to)
                return None
        _LOGGER.warning("Value %s is missing in API response", key)
        return None

    async def start(self):
        """Start the data refreshing task."""
        await self.fetch_data()
        self.refresh_task = asyncio.create_task(self.refresh_data())

    async def stop(self):
        """Stop the data refreshing task."""
        if self.refresh_task:
            self.refresh_task.cancel()
            try:
                await self.refresh_task
            except asyncio.CancelledError:
                pass

    async def async_start(self):
        """Start the data refreshing task."""
        try:
            # Fetch data
            await self._async_update_data()
            self.last_update_success = True
        except Exception as e:
            self.last_update_success = False
            _LOGGER.error(f"Error fetching data: {e}")
            raise ConfigEntryNotReady from e

    async def async_stop(self):
        """Stop the data refreshing task."""
        # You can add cleanup logic here if needed
        pass


async def create_buienalarm_coordinator(hass, config_entry, api, latitude, longitude, update_interval=DEFAULT_UPDATE_INTERVAL):
    # timeout = ClientTimeout(total=10)
    # client_session = ClientSession(timeout=timeout)
    # coordinator = BuienalarmCoordinator(hass, latitude, longitude, client_session, update_interval)
    client_session = ClientSession(timeout=API_TIMEOUT)
    coordinator = BuienalarmDataUpdateCoordinator(hass, config_entry, api, latitude, longitude, client_session, update_interval)

    await coordinator.start()
    # await coordinator.async_refresh()
    return coordinator


async def old_create_buienalarm_coordinator(
    hass: HomeAssistant,
    latitude: float,
    longitude: float,
    client_session: ClientSession,
    device_info: DeviceInfo,
) -> DataUpdateCoordinator:
    """Create and configure the Buienalarm coordinator."""
    _LOGGER.debug("Received latitude: %s, longitude: %s", latitude, longitude)
    # Define the update interval (e.g., 15 minutes)
    update_interval = timedelta(minutes=5)

    # Create the data coordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Define the update method to fetch data from your API
        update_method=_fetch_buienalarm_data,
        # Define the update interval
        update_interval=update_interval,
    )

    # Configure the coordinator with additional attributes as needed
    coordinator.latitude = latitude
    coordinator.longitude = longitude
    coordinator.client_session = client_session
    coordinator.device_info = device_info

    return coordinator


async def _fetch_buienalarm_data(coordinator: DataUpdateCoordinator) -> dict:
    """Fetch Buienalarm data from the API."""

    latitude = coordinator.latitude
    longitude = coordinator.longitude

    url = API_ENDPOINT.format(latitude, longitude)

    try:
        async with coordinator.client_session.get(url, timeout=API_TIMEOUT) as response:
            if response.status != 200:
                raise Exception("Error fetching data")

            data = await response.json()
            return data

    except Exception as e:
        raise Exception(f"Error fetching data: {e}")
