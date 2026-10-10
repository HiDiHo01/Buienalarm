"""DataUpdateCoordinator for the Buienalarm integration."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BuienalarmApiClient
from .const import API_ENDPOINT, API_TIMEOUT, DEFAULT_UPDATE_INTERVAL
from .exceptions import ApiError

_LOGGER: logging.Logger = logging.getLogger(__name__)


class BuienalarmDataUpdateCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Class to manage fetching data from the Buienalarm API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: BuienalarmApiClient,
        device_info: DeviceInfo,
        config_entry: ConfigEntry,
        update_interval: timedelta = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.device_info = device_info
        self.config_entry = config_entry
        self.url = API_ENDPOINT.format(api.latitude, api.longitude)
        self.api_last_updated: datetime | None = None

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name="Buienalarm Coordinator",
            update_interval=update_interval,
            config_entry=config_entry,
        )

    async def _async_setup(self) -> None:
        """Validate or retrieve initial data during setup."""
        try:
            await self.api.async_get_initial_data()
        except Exception as err:
            _LOGGER.error("Initial API setup failed: %s", err)
            raise ConfigEntryNotReady from err

    async def _async_update_data(self) -> dict[str, object]:
        """Fetch latest data from Buienalarm API."""
        try:
            async with asyncio.timeout(API_TIMEOUT):
                data = await self.api.async_get_data()
                self.api_last_updated = datetime.now(timezone.utc)
                return data
        except (ApiError, aiohttp.ClientError, TimeoutError) as error:
            _LOGGER.error("[COORD] Error updating data: %s", error)
            raise UpdateFailed(f"Error updating data: {error}") from error
        except Exception as err:
            _LOGGER.error("[COORD] Error updating Buienalarm data: %s", err)
            raise UpdateFailed(f"Error fetching Buienalarm data: {err}") from err
