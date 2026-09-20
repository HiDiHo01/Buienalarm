"""Entity descriptions for Buienalarm sensors."""

from typing import Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime, UnitOfVolumetricFlux

SENSOR_KEYS: list[dict] = [
    {
        "key": "nowcastmessage",
        "name": "Nowcast Message",
        "icon": "mdi:chat-alert",
    },
    {
        "key": "mycastmessage",
        "name": "Mycast Message",
        "icon": "mdi:chat-processing",
    },
    {
        "key": "precipitation_duration",
        "name": "Precipitation Duration",
        "icon": "mdi:clock-outline",
        "native_unit_of_measurement": UnitOfTime.MINUTES,
        "state_class": SensorStateClass.MEASUREMENT,
        "device_class": SensorDeviceClass.DURATION,
    },
    {
        "key": "precipitationrate_total",
        "name": "Total Precipitation Rate",
        "icon": "mdi:weather-pouring",
        "native_unit_of_measurement": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        "device_class": SensorDeviceClass.PRECIPITATION_INTENSITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "precipitationrate_hour",
        "name": "Hourly Precipitation Rate",
        "icon": "mdi:weather-pouring",
        "native_unit_of_measurement": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        "device_class": SensorDeviceClass.PRECIPITATION_INTENSITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "precipitationrate_now",
        "name": "Current Precipitation Rate",
        "icon": "mdi:weather-rainy",
        "native_unit_of_measurement": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        "device_class": SensorDeviceClass.PRECIPITATION_INTENSITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "precipitationrate_now_desc",
        "name": "Precipitation Description",
        "icon": "mdi:weather-cloudy-alert",
    },
    {
        "key": "precipitationtype_now",
        "name": "Precipitation Type",
        "icon": "mdi:weather-partly-rainy",
    },
    {
        "key": "next_precipitation",
        "name": "Next Precipitation In",
        "icon": "mdi:clock-start",
        "native_unit_of_measurement": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
    },
    {
        "key": "precipitation_periods",
        "name": "Precipitation Periods",
        "icon": "mdi:weather-rainy",
        "enabled_by_default": False,
    },
]

BINARY_SENSOR_DESCRIPTIONS: Final[tuple[BinarySensorEntityDescription, ...]] = (
    BinarySensorEntityDescription(
        key="precipitation_expected",
        translation_key="precipitation_expected",
        name="Neerslag verwacht",
        icon="mdi:weather-rainy",
    ),
    BinarySensorEntityDescription(
        key="currently_raining",
        translation_key="currently_raining",
        name="Het regent nu",
        icon="mdi:weather-rainy",
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
    BinarySensorEntityDescription(
        key="currently_snowing",
        translation_key="currently_snowing",
        name="Het sneeuwt nu",
        icon="mdi:weather-snowy",
        device_class=BinarySensorDeviceClass.MOISTURE,
    ),
)

SENSOR_DESCRIPTIONS: list[SensorEntityDescription] = [
    SensorEntityDescription(
        key=entry["key"],
        translation_key=entry.get("translation_key", entry["key"]),
        name=entry["name"],
        icon=entry.get("icon"),
        device_class=entry.get("device_class"),
        state_class=entry.get("state_class"),
        native_unit_of_measurement=entry.get("native_unit_of_measurement"),
        entity_registry_enabled_default=entry.get("enabled_by_default", True),
    )
    for entry in SENSOR_KEYS
]
