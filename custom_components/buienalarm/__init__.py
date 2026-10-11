"""Buienalarm integration initialization."""

# __init__.py
import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
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
    _LOGGER.debug(
        "[INIT] Migrating Buienalarm entry %s (v%s)", entry.entry_id, old_version
    )

    if old_version == 1:
        # 1️⃣ Uniek ID op basis van lat/lon bepalen
        lat = entry.options.get(CONF_LATITUDE, entry.data.get(CONF_LATITUDE))
        lon = entry.options.get(CONF_LONGITUDE, entry.data.get(CONF_LONGITUDE))
        if lat is None or lon is None:
            _LOGGER.error(
                "Cannot migrate entry %s: missing latitude/longitude", entry.entry_id
            )
            return False

        unique_id = f"{lat}_{lon}"

        # 2️⃣ Één atomaire update: unique_id + nieuwe versie
        hass.config_entries.async_update_entry(
            entry,
            version=2,  # ← verhoog versie hier
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


def _has_duplicate_entry(
    hass: HomeAssistant, entry: ConfigEntry, latitude: float, longitude: float
) -> bool:
    """Return True if an identical entry already exists."""
    target_unique_id = f"{latitude}_{longitude}"
    dup = any(
        existing.entry_id != entry.entry_id
        and (
            existing.unique_id == target_unique_id
            or (
                existing.options.get(CONF_LATITUDE, existing.data.get(CONF_LATITUDE))
                == latitude
                and existing.options.get(
                    CONF_LONGITUDE, existing.data.get(CONF_LONGITUDE)
                )
                == longitude
            )
        )
        for existing in hass.config_entries.async_entries(DOMAIN)
    )
    _LOGGER.debug(
        "[INIT_SETUP_ENTRY] Duplicate entry check for %s (%s, %s): %s",
        entry.entry_id,
        latitude,
        longitude,
        dup,
    )
    return dup


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Buienalarm integration from a config entry."""
    _LOGGER.debug(
        "[INIT_SETUP_ENTRY] Starting setup for entry_id=%s, title=%s",
        entry.entry_id,
        entry.title,
    )

    # Ensure storage
    hass.data.setdefault(DOMAIN, {})

    # Read coordinates safely
    lat_val = entry.options.get(CONF_LATITUDE, entry.data.get(CONF_LATITUDE))
    lon_val = entry.options.get(CONF_LONGITUDE, entry.data.get(CONF_LONGITUDE))
    if lat_val is None or lon_val is None:
        _LOGGER.error("[INIT_SETUP_ENTRY] Missing required latitude or longitude")
        return False

    latitude = float(lat_val)
    longitude = float(lon_val)
    _LOGGER.debug("[INIT_SETUP_ENTRY] Coordinates loaded: %s, %s", latitude, longitude)

    # Prevent duplicates based on effective coordinates
    if _has_duplicate_entry(hass, entry, latitude, longitude):
        _LOGGER.warning(
            "[INIT_SETUP_ENTRY] Duplicate config entry detected for (%s, %s): %s",
            latitude,
            longitude,
            entry.title,
        )
        return False

    name = entry.options.get(CONF_NAME, entry.data.get(CONF_NAME, NAME))
    unique_id = f"{latitude}_{longitude}"
    title = f"{name} ({latitude}, {longitude})"

    # Check if entry options altered location/identity or if data is missing coordinates
    options_lat = entry.options.get(CONF_LATITUDE)
    options_lon = entry.options.get(CONF_LONGITUDE)
    options_name = entry.options.get(CONF_NAME)

    if (
        (options_lat is not None and options_lat != entry.data.get(CONF_LATITUDE))
        or (options_lon is not None and options_lon != entry.data.get(CONF_LONGITUDE))
        or (options_name is not None and options_name != entry.data.get(CONF_NAME))
        or (entry.data.get(CONF_LATITUDE) is None)
        or (entry.data.get(CONF_LONGITUDE) is None)
    ):
        new_data = dict(entry.data)
        new_data[CONF_LATITUDE] = latitude
        new_data[CONF_LONGITUDE] = longitude
        new_data[CONF_NAME] = name
        new_data["location_id"] = unique_id
        new_data["location_name"] = name
        if "notification_limit" in entry.options:
            new_data["notification_limit"] = entry.options["notification_limit"]
        if "refresh_interval" in entry.options:
            new_data["refresh_interval"] = entry.options["refresh_interval"]

        _LOGGER.debug(
            "[INIT_SETUP_ENTRY] Updating entry identity for %s (%s, %s)",
            entry.entry_id,
            latitude,
            longitude,
        )
        hass.config_entries.async_update_entry(
            entry,
            title=title,
            unique_id=unique_id,
            data=new_data,
        )

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
        total=API_TIMEOUT,  # Total timeout for the request
        connect=10,  # Timeout for connection
        sock_read=10,  # Timeout for read after connection
        sock_connect=10,  # Timeout for socket connect
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

    # Configure refresh interval
    refresh_seconds = int(
        entry.options.get(
            "refresh_interval",
            entry.data.get("refresh_interval", SCAN_INTERVAL.total_seconds()),
        )
    )
    update_interval = timedelta(seconds=refresh_seconds)

    # Create coordinator
    try:
        coordinator = BuienalarmDataUpdateCoordinator(
            hass=hass,
            config_entry=entry,
            api=api,
            device_info=device_info,
            update_interval=update_interval,
        )
        _LOGGER.debug("[INIT_SETUP_ENTRY] Coordinator initialized: %s", coordinator)
    except Exception as err:
        _LOGGER.error("[INIT_SETUP_ENTRY] Failed to create coordinator: %s", err)
        raise ConfigEntryNotReady(
            "Failed to create coordinator for %s" % entry.title
        ) from err

    _LOGGER.debug(
        "[INIT_SETUP_ENTRY] Coordinator update_interval set to %s", update_interval
    )

    # --------------- Fetch first data -----------------
    _LOGGER.debug("[INIT_SETUP_ENTRY] Fetching initial data for %s", entry.title)
    try:
        # Perform initial data fetch
        # if not coordinator.last_update_success:
        #     await coordinator.async_request_refresh()
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.debug(
            "[INIT_SETUP_ENTRY] Initial data fetch successful for %s", entry.title
        )
    except UpdateFailed as err:
        _LOGGER.error(
            "[INIT_SETUP_ENTRY] Initial data fetch failed for %s: %s", entry.title, err
        )
        raise ConfigEntryNotReady(f"Failed to fetch initial data for {entry.title}")
    # --------------------------------------------------

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _LOGGER.debug(
        "[INIT_SETUP_ENTRY] Coordinator stored in hass.data[%s][%s]",
        DOMAIN,
        entry.entry_id,
    )
    _LOGGER.debug(
        "[INIT_SETUP_ENTRY] Config entry %s with ID %s set up successfully",
        entry.title,
        entry.entry_id,
    )

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
        _LOGGER.debug(
            "[INIT_UNLOAD_ENTRY] Config entry %s with ID %s unloaded",
            entry.title,
            entry.entry_id,
        )
        _LOGGER.debug("[INIT_UNLOAD_ENTRY] Unloading platforms: %s", PLATFORMS)
        _LOGGER.debug("[INIT_UNLOAD_ENTRY] Unloading %s", unloaded)
        return unloaded
    _LOGGER.warning(
        "[INIT_UNLOAD_ENTRY] Failed to unload entry %s with ID %s from platforms",
        entry.title,
        entry.entry_id,
    )
    _LOGGER.debug("[INIT_UNLOAD_ENTRY] Unloading platforms: %s", PLATFORMS)
    _LOGGER.debug("[INIT_UNLOAD_ENTRY] Unloading %s", unloaded)
    return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle reload of a config entry."""
    _LOGGER.debug(
        "[INIT_RELOAD_ENTRY] Reloading config entry %s with ID %s",
        entry.title,
        entry.entry_id,
    )
    await hass.config_entries.async_reload(entry.entry_id)
