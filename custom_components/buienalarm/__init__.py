# __init__.py
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .api import BuienalarmApiClient
from .const import API_CONF_URL, DOMAIN, NAME, PLATFORMS, SCAN_INTERVAL, VERSION
from .coordinator import BuienalarmDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__name__)

_LOGGER.debug("__init__ gestart")


async def async_setup(hass: HomeAssistant, _: dict) -> bool:
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    _LOGGER.debug("__init__ async_setup_entry")

    # Check for duplicate entries
    # existing_entries = hass.config_entries.async_entries(DOMAIN)
    # for existing_entry in existing_entries:
    #     if entry.data == existing_entry.data:
    #         _LOGGER.debug("__init__ duplicate found")
    # return False  # Duplicate entry found, do not set up

    # Check for duplicate entries
    # if any(entry.data == e.data for e in hass.config_entries.async_entries(DOMAIN)):
    #     _LOGGER.warning("Duplicate entry found for %s: %s", entry.title, entry.data)
    #     return False

    hass.data.setdefault(DOMAIN, {})

    try:
        latitude = entry.data[CONF_LATITUDE]
        longitude = entry.data[CONF_LONGITUDE]
        network = entry.data.get("network")
        if network is None:
            _LOGGER.error("Missing required 'network' in config entry data")
            return False
    except KeyError as e:
        _LOGGER.error("Missing required configuration: %s", e)
        return False

    # refresh_interval = entry.data.get("refresh_interval")
    # refresh_interval = entry.options.get("refresh_interval")

    # Check if the config entry exists and print its options
    if entry.options:
        _LOGGER.debug("Config entry options: %s", entry.options)
    else:
        _LOGGER.debug("Config entry options are empty")

    session = async_get_clientsession(hass, verify_ssl=True)
    client = BuienalarmApiClient(latitude, longitude, session, hass)

    device_info = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=NAME,
        name=entry.title,
        model="Neerslag data",
        configuration_url=API_CONF_URL,
        sw_version=VERSION,
    )

    try:
        coordinator = BuienalarmDataUpdateCoordinator(
            hass=hass,
            client=client,
            device_info=device_info,
            config_entry=entry,
        )
    except Exception as err:
        raise ConfigEntryNotReady("Unexpected failure") from err
    
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Fetch the config entry options directly from the entry
    refresh_interval = entry.options.get("refresh_interval", SCAN_INTERVAL.total_seconds())

    coordinator.refresh_interval = refresh_interval

    _LOGGER.debug("coordinator attributes: %s", dir(coordinator))
    _LOGGER.debug("coordinator attribute refresh_interval: %s", coordinator.refresh_interval)
    _LOGGER.debug("coordinator attribute options: %s", coordinator.options)
    # await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady(f"Failed to initialize {entry.title}")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("entry unloaded", entry.title)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.debug("entry reloaded")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
