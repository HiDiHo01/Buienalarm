"""Buienalarm integration initialization."""
# __init__.py
import logging

import aiohttp
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
    API_TIMEOUT,
    DOMAIN,
    NAME,
    PLATFORMS,
    SCAN_INTERVAL,
    VERSION,
)
from .coordinator import BuienalarmDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__name__)

_LOGGER.debug("[INIT] __init__.py loaded for Buienalarm integration")

__all__: list[str] = [
    "async_setup",
    "async_setup_entry",
    "async_unload_entry",
    "async_reload_entry",
]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old Buienalarm entries to version 2 (add unique_id)."""
    old_version = entry.version
    _LOGGER.debug("[INIT] Migrating Buienalarm entry %s (v%s)", entry.entry_id, old_version)

    if old_version == 1:
        # 1️⃣ Uniek ID op basis van lat/lon bepalen
        lat = entry.data.get(CONF_LATITUDE)
        lon = entry.data.get(CONF_LONGITUDE)
        if lat is None or lon is None:
            _LOGGER.error(
                "Cannot migrate entry %s: missing latitude/longitude", entry.entry_id
            )
            return False

        unique_id = f"{lat}_{lon}"

        # 2️⃣ Één atomaire update: unique_id + nieuwe versie
        hass.config_entries.async_update_entry(
            entry,
            version=2,          # ← verhoog versie hier
            unique_id=unique_id,
        )
        _LOGGER.info(
            "Entry %s migrated to v2 with unique_id=%s", entry.entry_id, unique_id
        )

    return True


async def async_setup(hass: HomeAssistant, _: dict[str, object]) -> bool:
    """Return True so that Home Assistant can import the integration.

    YAML-configuratie wordt niet ondersteund; deze functie voorkomt
    slechts dat Home Assistant een fout gooit wanneer er toch een
    YAML-entry zou bestaan.
    """
    _LOGGER.debug("[INIT_SETUP] async_setup called - YAML config unsupported")
    return True


def _has_duplicate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Return True if an identical entry already exists."""
    dup = any(
        existing.entry_id != entry.entry_id and existing.data == entry.data
        for existing in hass.config_entries.async_entries(DOMAIN)
    )
    _LOGGER.debug("[INIT_SETUP_ENTRY] Duplicate entry check for %s: %s", entry.entry_id, dup)
    return dup


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Buienalarm integration from a config entry."""
    _LOGGER.debug("[INIT_SETUP_ENTRY] Starting setup for entry_id=%s, title=%s", entry.entry_id, entry.title)

    # Prevent duplicates
    if _has_duplicate_entry(hass, entry):
        _LOGGER.warning("[INIT_SETUP_ENTRY] Duplicate config entry detected: %s", entry.title)
        return False

    # Ensure storage
    hass.data.setdefault(DOMAIN, {})

    # Read coordinates
    try:
        latitude = entry.data[CONF_LATITUDE]
        longitude = entry.data[CONF_LONGITUDE]
        _LOGGER.debug("[INIT_SETUP_ENTRY] Coordinates: latitude=%s, longitude=%s", latitude, longitude)
    except KeyError as e:
        _LOGGER.error("[INIT_SETUP_ENTRY] Missing required config: %s", e)
        return False

    # refresh_interval = entry.data.get("refresh_interval")
    # refresh_interval = entry.options.get("refresh_interval")

    # Check if the config entry exists and print its options
    if entry.options:
        _LOGGER.debug("[INIT_SETUP_ENTRY] Entry options: %s", entry.options)
    else:
        _LOGGER.debug("[INIT_SETUP_ENTRY] No entry options set; using defaults")

    # Create HTTP session
    session = async_get_clientsession(hass, verify_ssl=True)
    _LOGGER.debug("[INIT_SETUP_ENTRY] aiohttp ClientSession acquired: %s", session)
    timeout = aiohttp.ClientTimeout(
        total=API_TIMEOUT,     # Total timeout for the request
        connect=10,            # Timeout for connection
        sock_read=10,          # Timeout for read after connection
        sock_connect=10        # Timeout for socket connect
    )

    # Initialize API client
    api = BuienalarmApiClient(latitude, longitude, session, hass)
    _LOGGER.debug("[INIT_SETUP_ENTRY] BuienalarmApiClient created: %s", api)

    # Prepare device info
    device_info = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=NAME,
        name=entry.title,
        model="Neerslag data",
        configuration_url=API_CONF_URL,
        sw_version=VERSION,
    )
    _LOGGER.debug("[INIT_SETUP_ENTRY] DeviceInfo prepared: %s", device_info)

    # Create coordinator
    try:
        coordinator = BuienalarmDataUpdateCoordinator(
            hass=hass,
            config_entry=entry,
            api=api,
            device_info=device_info,

        )
        _LOGGER.debug("[INIT_SETUP_ENTRY] Coordinator initialized: %s", coordinator)
    except Exception as err:
        _LOGGER.error("[INIT_SETUP_ENTRY] Failed to create coordinator: %s", err)
        # raise ConfigEntryNotReady(f"Failed to create coordinator for {entry.title}")
        raise ConfigEntryNotReady("Failed to create coordinator for %s" % entry.title) from err

    # Configure refresh
    # Fetch the config entry options directly from the entry
    refresh_interval = int(entry.options.get("refresh_interval", SCAN_INTERVAL.total_seconds()))
    coordinator.refresh_interval = refresh_interval
    _LOGGER.debug("[INIT_SETUP_ENTRY] Coordinator update_interval set to %s seconds", refresh_interval)
    _LOGGER.debug("[INIT_SETUP_ENTRY] Coordinator attributes: %s", dir(coordinator))
    _LOGGER.debug("[INIT_SETUP_ENTRY] Coordinator attribute refresh_interval: %s", coordinator.refresh_interval)
    _LOGGER.debug("[INIT_SETUP_ENTRY] Coordinator attribute options: %s", coordinator.options)

    # --------------- Fetch first data -----------------
    _LOGGER.debug("[INIT_SETUP_ENTRY] Fetching initial data for %s", entry.title)
    try:
        # Perform initial data fetch
        # if not coordinator.last_update_success:
        #     await coordinator.async_request_refresh()
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.debug("[INIT_SETUP_ENTRY] Initial data fetch successful for %s", entry.title)
    except UpdateFailed as err:
        _LOGGER.error("[INIT_SETUP_ENTRY] Initial data fetch failed for %s: %s", entry.title, err)
        raise ConfigEntryNotReady(f"Failed to fetch initial data for {entry.title}")
    # --------------------------------------------------

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _LOGGER.debug("[INIT_SETUP_ENTRY] Coordinator stored in hass.data[%s][%s]", DOMAIN, entry.entry_id)
    _LOGGER.debug("[INIT_SETUP_ENTRY] Config entry %s with ID %s set up successfully", entry.title, entry.entry_id)

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("[INIT_SETUP_ENTRY] Forwarded setup to platforms: %s", PLATFORMS)

    # Register reload listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    _LOGGER.debug("[INIT_SETUP_ENTRY] Reload listener registered")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    _LOGGER.debug("[INIT_UNLOAD_ENTRY] Unloading entry_id=%s", entry.entry_id)
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.debug("[INIT_UNLOAD_ENTRY] Config entry %s with ID %s unloaded", entry.title, entry.entry_id)
        _LOGGER.debug("[INIT_UNLOAD_ENTRY] Unloading platforms: %s", PLATFORMS)
        _LOGGER.debug("[INIT_UNLOAD_ENTRY] Unloading %s", unloaded)
        return unloaded
    _LOGGER.warning("[INIT_UNLOAD_ENTRY] Failed to unload entry %s with ID %s from platforms",
                    entry.title, entry.entry_id)
    _LOGGER.debug("[INIT_UNLOAD_ENTRY] Unloading platforms: %s", PLATFORMS)
    _LOGGER.debug("[INIT_UNLOAD_ENTRY] Unloading %s", unloaded)
    return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle reload of a config entry."""
    _LOGGER.debug("[INIT_RELOAD_ENTRY] Reloading config entry %s with ID %s", entry.title, entry.entry_id)
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
