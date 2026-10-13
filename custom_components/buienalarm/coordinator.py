"""Buienalarm DataUpdateCoordinator."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import BuienalarmApiClient
from .const import API_ENDPOINT, DEFAULT_UPDATE_INTERVAL

_LOGGER: logging.Logger = logging.getLogger(__name__)

_LOGGER.debug("[COORD] coordinator loaded")

_API_TIMEOUT = 30


class BuienalarmDataUpdateCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Class to manage fetching data from the Buienalarm API."""

    options: dict[str, object] | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        api: BuienalarmApiClient,
        device_info: DeviceInfo,
        config_entry: ConfigEntry,
        update_interval: timedelta = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Initialize the Buienalarm data update coordinator."""
        _LOGGER.debug(
            "[COORD INIT] DataUpdateCoordinator initialized for entry_id=%s",
            config_entry.entry_id,
        )

        self.hass = hass
        self.api = api
        self.device_info = device_info
        self.config_entry = config_entry
        self.url = API_ENDPOINT.format(api.latitude, api.longitude)
        self.entities: list[object] = []
        self.api_last_updated: datetime | None = None
        self.options = config_entry.options if config_entry else None

        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name="Buienalarm Coordinator",
            update_interval=update_interval,
            update_method=self._async_update_data,
            setup_method=self._async_setup,
            config_entry=config_entry,
        )
        _LOGGER.debug("[COORD INIT] DataUpdateCoordinator initialized")

    async def _async_setup(self) -> None:
        """Run once before first update to validate auth or fetch static data."""
        _LOGGER.debug("Running _async_setup for BuienalarmCoordinator")
        try:
            await self.api.async_get_initial_data()
        except Exception as err:
            _LOGGER.error("Initial API setup failed: %s", err)
            raise ConfigEntryNotReady from err

    async def _async_update_data(self) -> dict[str, object]:
        """Fetch data from the Buienalarm API asynchronously."""
        _LOGGER.debug(
            "[COORD UPDATE] Starting _async_update_data with timeout: %s", _API_TIMEOUT
        )
        try:
            async with asyncio.timeout(_API_TIMEOUT):
                data = await self.api.async_get_data()
                self.api_last_updated = datetime.now(timezone.utc)
                return data
        except Exception as err:
            _LOGGER.error("[COORD] Error updating Buienalarm data: %s", err)
            raise UpdateFailed("Error fetching Buienalarm data") from err
