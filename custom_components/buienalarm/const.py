# const.py
"""Constants for Buienalarm."""


from datetime import timedelta
from typing import Final

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTime, UnitOfVolumetricFlux

# API Configuration
API_ENDPOINT: Final[str] = "https://imn-rust-lb.infoplaza.io/v4/nowcast/ba/timeseries/{}/{}"
API_TIMEOUT: Final[int] = 30
API_TIMEZONE: Final[str] = "Europe/Amsterdam"
API_CONF_URL: Final[str] = "https://buienalarm.nl"
DATA_KEY: Final[str] = "data"

# Integration metadata
NAME: Final[str] = "Buienalarm"
DOMAIN: Final[str] = "buienalarm"
VERSION: Final[str] = "2025.10.18"
ATTR_ATTRIBUTION: Final[str] = "Data provided by Buienalarm"

# Default configuration
DEFAULT_NAME: Final[str] = NAME

# API and Data Update intervals
SCAN_INTERVAL: Final[timedelta] = timedelta(minutes=5)
DATA_REFRESH_INTERVAL: Final[int] = 300
DEFAULT_UPDATE_INTERVAL: Final[timedelta] = timedelta(minutes=5)

# Supported platforms
# BINARY_SENSOR: Final[str] = "binary_sensor"
SENSOR: Final[str] = "sensor"
# PLATFORMS: Final[list[str]] = [BINARY_SENSOR, SENSOR]
PLATFORMS: Final[list[str]] = [SENSOR]

# Icon templates (not in use)
ICON_TEMPLATE: Final[str] = "mdi:weather-{}"

# Sensor definitions
SENSORS: Final[list[dict[str, object]]] = [
    {
        "name": "Melding",
        "icon": "mdi:weather-pouring",
        "key": "nowcastmessage",
        "unit_of_measurement": None,
        "device_class": None,
        "state_class": None,
    },
    {
        "name": "Mijn melding",
        "icon": "mdi:weather-pouring",
        "key": "mycastmessage",
        "unit_of_measurement": None,
        "device_class": None,
        "state_class": None,
    },
    {
        "name": "Neerslag omschrijving",
        "icon": "mdi:weather-rainy",
        "key": "precipitationrate_now_desc",
        "unit_of_measurement": None,
        "device_class": None,
        "state_class": None,
    },
    {
        "name": "Soort neerslag",
        "icon": "mdi:weather-pouring",
        "key": "precipitationtype_now",
        "unit_of_measurement": None,
        "device_class": None,
        "state_class": None,
    },
    {
        "name": "Volgende neerslag",
        "icon": "mdi:clock-outline",
        "key": "next_precipitation",
        "unit_of_measurement": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "state_class": None,
    },
    {
        "name": "Duur neerslag",
        "icon": "mdi:clock-outline",
        "key": "precipitation_duration",
        "unit_of_measurement": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "state_class": None,
    },
    {
        "name": "Neerslag",
        "icon": "mdi:weather-rainy",
        "key": "precipitationrate_now",
        "unit_of_measurement": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        "device_class": SensorDeviceClass.PRECIPITATION_INTENSITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Neerslag komend uur",
        "icon": "mdi:weather-rainy",
        "key": "precipitationrate_hour",
        "unit_of_measurement": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        "device_class": SensorDeviceClass.PRECIPITATION_INTENSITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Neerslag verwacht",
        "icon": "mdi:weather-rainy",
        "key": "precipitationrate_total",
        "unit_of_measurement": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        "device_class": SensorDeviceClass.PRECIPITATION_INTENSITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Neerslag periodes",
        "icon": "mdi:weather-rainy",
        "key": "precipitation_periods",
        "unit_of_measurement": None,
        "device_class": None,
        "state_class": None,
    },
]
