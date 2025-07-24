# coordinator.py
import asyncio
import logging
from datetime import timedelta
from typing import Callable

import aiohttp
import async_timeout
import requests
from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BuienalarmApiClient
from .const import API_ENDPOINT, API_TIMEOUT, DEFAULT_UPDATE_INTERVAL

_LOGGER: logging.Logger = logging.getLogger(__name__)

_LOGGER.debug("[COORD] coordinator loaded")

_API_TIMEOUT = ClientTimeout(
    total=30,       # hard‑stop; moet < HA default (15 s) blijven
    connect=5,      # connectie‑timeout
    sock_read=20,   # lees‑timeout
    sock_connect=5  # connectie‑timeout
)


class BuienalarmDataUpdateCoordinator(DataUpdateCoordinator):
    _LOGGER.debug("[COORD] coordinator: class BuienalarmDataUpdateCoordinator loaded")
    """Class to manage fetching data from the API."""
    options: dict = None

    def __init__(
        self,
        hass: HomeAssistant,
        api: BuienalarmApiClient,
        device_info: DeviceInfo,
        config_entry: ConfigEntry,
        update_interval: timedelta = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        _LOGGER.debug(
            "[COORD INIT] api=%s, entry_id=%s, update_interval=%s, device_info=%s",
            api,
            config_entry.entry_id,
            update_interval,
            device_info,
        )

        # Initialize coordinator attributes
        self.hass = hass
        self.api = api
        self.device_info = device_info
        self.config_entry = config_entry
        self.url = API_ENDPOINT.format(api.latitude, api.longitude)
        _LOGGER.debug("[COORD INIT] Using API URL: %s", self.url)
        self.entities = []  # Create an empty list to store associated entities
        # self.last_update_success = False

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name="Buienalarm Coordinator",
            update_interval=update_interval,
            update_method=self._async_update_data,
            setup_method=self._async_setup,
        )
        _LOGGER.debug("[COORD INIT] DataUpdateCoordinator initialized")

    async def async_add_listener(self, listener, update_supported=True):
        # Implement the logic to add a listener here
        # This method allows entities to register themselves as listeners to receive updates
        pass

    async def fetch_data(self):
        """Fetch data from the Buienalarm API asynchronously.
        Wordt nioet uitegevoerd
        """
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

    async def _async_setup(self) -> None:
        """
        Run once before first update.
        Use this to validate auth or fetch static data.
        """
        _LOGGER.debug("Running _async_setup for BuienalarmCoordinator")
        try:
            # bv. valideren van locatietoegang of ophalen stationsinformatie
            await self.api.async_get_initial_data()
        except Exception as err:
            _LOGGER.error("Initial API setup failed: %s", err)
            raise ConfigEntryNotReady from err

    async def _async_update_data(self):
        _LOGGER.debug("[COORD UPDATE] Starting _async_update_data for URL: %s with timeout: %s", self.url, _API_TIMEOUT)
        try:
            async with async_timeout.timeout(30):
                return await self.api.async_get_data()
                response = await self.hass.async_add_executor_job(
                    requests.get, self.url
                )
                _LOGGER.debug(
                    "[COORD] HTTP status: %s, headers: %s",
                    response.status_code,
                    response.headers,
                )
                response.raise_for_status()
                data = response.json()
                _LOGGER.debug("[COORD] JSON data: %s", data)
                return data
        except (requests.RequestException, ValueError) as error:
            _LOGGER.error("[COORD] Error updating data: %s", error)
            raise UpdateFailed(f"Error updating data: {error}") from error
        except Exception as err:
            _LOGGER.error("[COORD] Error updating Buienalarm data: %s", err)
            raise UpdateFailed("Error fetching Buienalarm data") from err

    async def old_async_update_data(self) -> dict[str, object]:
        """Query de Buienalarm‑API (1 retry)."""
        _LOGGER.debug("[COORD UPDATE] Starting _async_update_data for URL: %s", self.url)
        _LOGGER.debug(
            "[COORDINATOR] Will fetch URL: %s using %s",
            self.url,
            self.hass.loop.is_running(),
        )
        _LOGGER.debug(f"Type of client_session: {type(self.api)}")
        url = self.url
        for attempt in (1, 2):  # max 2 pogingen
            try:
                _LOGGER.debug("[COORD UPDATE] Fetch try %s: %s", attempt, url)
                return await self.api.async_get_data(timeout=_API_TIMEOUT)
            except asyncio.TimeoutError:
                _LOGGER.warning(
                    "[COORD UPDATE] Timeout (%ss) bij poging %s",
                    _API_TIMEOUT.total, attempt,
                )
            except (ClientResponseError, aiohttp.ClientError) as exc:
                _LOGGER.error("[COORD UPDATE] HTTP‑fout bij poging %s: %s", attempt, exc)
                _LOGGER.error(
                    "[COORD UPDATE] HTTP error fetching data: status=%s, message=%s",
                    exc.status,
                    exc.message,
                )
                raise UpdateFailed(exc) from exc
        raise UpdateFailed("Alle pogingen verlopen")

    async def old_refresh_data(self):
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
                _LOGGER.warning("Value %s with key %s can't be converted to %s",
                                self.data.get(key, None), key, convert_to)
                return None
        _LOGGER.warning("Value %s is missing in API response", key)
        return None

    async def old_start(self):
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
    client_session = ClientSession(timeout=API_TIMEOUT)
    coordinator = BuienalarmDataUpdateCoordinator(
        hass, config_entry, api, latitude, longitude, client_session, update_interval)

    await coordinator.start()
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
