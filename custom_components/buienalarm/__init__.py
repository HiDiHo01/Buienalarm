"""Buienalarm integration initialization."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import BuienalarmApiClient
from .const import (
    API_CONF_URL,
    DOMAIN,
    NAME,
    PLATFORMS,
    SCAN_INTERVAL,
    VERSION,
)
from .coordinator import BuienalarmDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__name__)

type BuienalarmConfigEntry = ConfigEntry[BuienalarmDataUpdateCoordinator]

__all__: list[str] = [
    "async_setup",
    "async_setup_entry",
    "async_unload_entry",
    "async_reload_entry",
]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old Buienalarm entries to version 2 (add unique_id)."""
    old_version = entry.version
    _LOGGER.debug("Migrating Buienalarm entry %s (v%s)", entry.entry_id, old_version)

    if old_version == 1:
        lat = entry.data.get(CONF_LATITUDE)
        lon = entry.data.get(CONF_LONGITUDE)
        if lat is None or lon is None:
            _LOGGER.error(
                "Cannot migrate entry %s: missing coordinates", entry.entry_id
            )
            return False

        unique_id = f"{lat}_{lon}"
        hass.config_entries.async_update_entry(
            entry,
            version=2,
            unique_id=unique_id,
        )
        _LOGGER.info(
            "Entry %s migrated to v2 with unique_id=%s", entry.entry_id, unique_id
        )

    return True


async def async_setup(hass: HomeAssistant, _: dict[str, object]) -> bool:
    """Set up integration (YAML configuration is unsupported)."""
    return True


def _has_duplicate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Return True if an identical entry already exists."""
    return any(
        existing.entry_id != entry.entry_id and existing.data == entry.data
        for existing in hass.config_entries.async_entries(DOMAIN)
    )


async def async_setup_entry(hass: HomeAssistant, entry: BuienalarmConfigEntry) -> bool:
    """Set up Buienalarm integration from a config entry."""
    _LOGGER.debug("Setting up entry_id=%s, title=%s", entry.entry_id, entry.title)

    if _has_duplicate_entry(hass, entry):
        _LOGGER.warning("Duplicate config entry detected: %s", entry.title)
        return False

    try:
        latitude = entry.data[CONF_LATITUDE]
        longitude = entry.data[CONF_LONGITUDE]
    except KeyError as err:
        _LOGGER.error("Missing required config: %s", err)
        return False

    session = async_get_clientsession(hass, verify_ssl=True)
    api = BuienalarmApiClient(
        latitude, longitude, session, hass, entry_id=entry.entry_id
    )

    device_info = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=NAME,
        name=entry.title,
        model="Neerslag data",
        configuration_url=API_CONF_URL,
        sw_version=VERSION,
    )

    refresh_seconds = int(
        entry.options.get("refresh_interval", SCAN_INTERVAL.total_seconds())
    )
    update_interval = timedelta(seconds=refresh_seconds)

    try:
        coordinator = BuienalarmDataUpdateCoordinator(
            hass=hass,
            config_entry=entry,
            api=api,
            device_info=device_info,
            update_interval=update_interval,
        )
    except Exception as err:
        _LOGGER.error("Failed to create coordinator: %s", err)
        raise ConfigEntryNotReady(
            f"Failed to create coordinator for {entry.title}"
        ) from err

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        _LOGGER.error("Initial data fetch failed for %s: %s", entry.title, err)
        raise ConfigEntryNotReady(
            f"Failed to fetch initial data for {entry.title}"
        ) from err
    except Exception as err:
        _LOGGER.error("Failed to refresh initial data for %s: %s", entry.title, err)
        raise ConfigEntryNotReady(
            f"Failed to create coordinator for {entry.title}"
        ) from err

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BuienalarmConfigEntry) -> bool:
    """Handle removal of an entry."""
    _LOGGER.debug("Unloading entry_id=%s", entry.entry_id)
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        return unloaded
    return False


async def async_reload_entry(hass: HomeAssistant, entry: BuienalarmConfigEntry) -> None:
    """Handle reload of a config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
