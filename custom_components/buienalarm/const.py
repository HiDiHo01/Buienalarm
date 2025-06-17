"""Constants for Buienalarm."""
# const.py

from datetime import timedelta
from typing import Any, Final

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTime, UnitOfVolumetricFlux

# API
API_ENDPOINT: Final[str] = "https://cdn.buienalarm.nl/api/4.0/nowcast/timeseries/{}/{}"
API_TIMEOUT: Final[int] = 15
API_TIMEZONE: Final[str] = "Europe/Amsterdam"
API_CONF_URL: Final[str] = "https://buienalarm.nl"
DATA_KEY: Final[str] = "data"

# Base component constants.
NAME: Final[str] = "Buienalarm"
DOMAIN: Final[str] = "buienalarm"
VERSION: Final[str] = "2025.6.17"
ATTRIBUTION: Final[str] = "Data provided by Buienalarm"
ATTR_ATTRIBUTION: Final[str] = "Data provided by Buienalarm"
CONF_ATTRIBUTION: Final[str] = "Data provided by Buienalarm"

# Defaults
DEFAULT_NAME: Final[str] = NAME

# API and Data Refresh
SCAN_INTERVAL: Final[timedelta] = timedelta(minutes=5)
DATA_REFRESH_INTERVAL: Final[int] = 300

# Platforms.
# BINARY_SENSOR: Final[str] = "binary_sensor"
SENSOR: Final[str] = "sensor"
# PLATFORMS: Final[list[str]] = [BINARY_SENSOR, SENSOR]
PLATFORMS: Final[list[str]] = [SENSOR]

# Icon templates (not in use)
ICON_TEMPLATE: Final[str] = "mdi:weather-{}"

# Sensors
SENSORS: Final[list[dict[str, Any]]] = [
    {
        "name": "Buienalarm",
        "icon": "mdi:weather-pouring",
        "key": "nowcastmessage",
        "attributes": [],
        "unit_of_measurement": None,
        "device_class": None,
        "state_class": None,
    },
    {
        "name": "My Buienalarm",
        "icon": "mdi:weather-pouring",
        "key": "mycastmessage",
        "attributes": [],
        "unit_of_measurement": None,
        "device_class": None,
        "state_class": None,
    },
    {
        "name": "Neerslag omschrijving",
        "icon": "mdi:weather-rainy",
        "key": "precipitationrate_now_desc",
        "attributes": [],
        "unit_of_measurement": None,
        "device_class": None,
        "state_class": None,
    },
    {
        "name": "Soort neerslag",
        "icon": "mdi:weather-pouring",
        "key": "precipitationtype_now",
        "attributes": [],
        "unit_of_measurement": None,
        "device_class": None,
        "state_class": None,
    },
    {
        "name": "Duur neerslag",
        "icon": "mdi:clock-outline",
        "key": "precipitation_duration",
        "attributes": [],
        "unit_of_measurement": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "state_class": None,
    },
    {
        "name": "Neerslag",
        "icon": "mdi:weather-rainy",
        "attributes": [],
        "key": "precipitationrate_now",
        "unit_of_measurement": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        "device_class": SensorDeviceClass.PRECIPITATION_INTENSITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Neerslag komend uur",
        "icon": "mdi:weather-rainy",
        "attributes": [],
        "key": "precipitationrate_hour",
        "unit_of_measurement": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        "device_class": SensorDeviceClass.PRECIPITATION_INTENSITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Neerslag verwacht",
        "icon": "mdi:weather-rainy",
        "attributes": [],
        "key": "precipitationrate_total",
        "unit_of_measurement": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        "device_class": SensorDeviceClass.PRECIPITATION_INTENSITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
]
