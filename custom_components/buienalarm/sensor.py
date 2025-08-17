# sensor.py
import logging
from datetime import timedelta
from typing import Final

import requests
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, UnitOfTime, UnitOfVolumetricFlux
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import API_ENDPOINT, ATTR_ATTRIBUTION, DOMAIN, SENSORS
from .coordinator import BuienalarmDataUpdateCoordinator
from .entity import BuienalarmEntity, BuienalarmSensorEntity
from .sensor_types import SENSOR_DESCRIPTIONS

_LOGGER = logging.getLogger(__name__)


old_SENSOR_DESCRIPTIONS: Final[list[SensorEntityDescription]] = [
    SensorEntityDescription(
        key="nowcastmessage",
        name="Buienalarm",
        icon="mdi:weather-pouring",
    ),
    SensorEntityDescription(
        key="mycastmessage",
        name="My Buienalarm",
        icon="mdi:weather-pouring",
    ),
    SensorEntityDescription(
        key="precipitationrate_now_description",
        name="Neerslag omschrijving",
        icon="mdi:weather-rainy",
    ),
    SensorEntityDescription(
        key="precipitationtype_now",
        name="Soort neerslag",
        icon="mdi:weather-pouring",
    ),
    SensorEntityDescription(
        key="next_precipitation",
        name="Next precipitation",
        icon="mdi:clock-outline",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
    ),
    SensorEntityDescription(
        key="precipitation_duration",
        name="Duur neerslag",
        icon="mdi:clock-outline",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
    ),
    SensorEntityDescription(
        key="precipitationrate_now",
        name="Neerslag",
        icon="mdi:weather-rainy",
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="precipitationrate_hour",
        name="Neerslag komend uur",
        icon="mdi:weather-rainy",
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="precipitationrate_total",
        name="Neerslag verwacht",
        icon="mdi:weather-rainy",
        native_unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

# Sensor data update coordinator for Buienalarm
# This coordinator fetches data from the Buienalarm API and provides it to sensor entities.


class BuienalarmDataUpdateCoordinator(DataUpdateCoordinator[dict[str, object]]):
    _LOGGER.debug("[SENSOR COORD] Initializing sync coordinator in sensor.py")

    def __init__(self,
                 hass: HomeAssistant,
                 latitude: float,
                 longitude: float,
                 config_entry: ConfigEntry
                 ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.url = API_ENDPOINT.format(latitude, longitude)
        _LOGGER.debug("[SENSOR COORD] URL set to %s", self.url)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),  # set update interval
            always_update=True,  # of False indien __eq__ kan vergelijken
            config_entry=config_entry,
        )
        _LOGGER.debug("[SENSOR COORD] Initialized with URL: %s", self.url)

    async def _async_update_data(self) -> dict[str, object]:
        """Fetch the latest data from Buienalarm."""
        _LOGGER.debug("[SENSOR COORD] _async_update_data called")
        try:
            # response = await self.api.async_get_data()
            response = await self.hass.async_add_executor_job(
                requests.get, self.url
            )
            _LOGGER.debug(
                "[SENSOR COORD] HTTP status: %s, headers: %s",
                response.status_code,
                response.headers,
            )
            response.raise_for_status()
            data = response.json()
            _LOGGER.debug("[SENSOR COORD] JSON data: %s", data)
            return data
        except (requests.RequestException, ValueError) as error:
            _LOGGER.error("[SENSOR COORD] Error updating data: %s", error)
            raise UpdateFailed(f"Error updating Buienalarm data: {error}") from error


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up Buienalarm sensors from config entry.

    This function creates a coordinator, fetches initial data,
    and adds sensor entities.
    """
    _LOGGER.debug("[SENSOR SETUP] Setting up Buienalarm sensors for %s", config_entry.unique_id)
    _LOGGER.debug("[SENSOR SETUP] async_setup_entry called for %s", config_entry.entry_id)

    latitude = config_entry.data.get("latitude")
    longitude = config_entry.data.get("longitude")

    _LOGGER.debug(
        "[SENSOR SETUP] Coordinates from entry: lat=%s, lon=%s", latitude, longitude
    )
    coordinator = BuienalarmDataUpdateCoordinator(hass, latitude, longitude, config_entry)
    _LOGGER.debug("[SENSOR SETUP] Coordinator created: %s", coordinator)

    # Perform initial refresh to warm up data
    try:
        # Prefer waiting – the tests and most users expect initial data
        # await coordinator.async_config_entry_first_refresh()

        # Start refresh as background task (niet awaiten!)
        task = hass.async_create_task(coordinator.async_config_entry_first_refresh())
        config_entry.async_on_unload(task.cancel)
        _LOGGER.debug(
            "[SENSOR SETUP] Initial refresh completed: success=%s",
            coordinator.last_update_success,
        )
    except UpdateFailed as err:
        _LOGGER.error("[SENSOR SETUP] Initial data fetch failed: %s", err)
        return False

    """Store the coordinator in hass.data for later access."""
    _LOGGER.debug("[SENSOR SETUP] Storing coordinator in hass.data for entry %s", config_entry.entry_id)
    if DOMAIN not in hass.data:
        _LOGGER.debug("[SENSOR SETUP] Initializing hass.data[%s]", DOMAIN)
        # Persist the coordinator in hass.data
        hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator

    # old_sensors
    sensors1: list[SensorEntity] = [
        BuienalarmSensor(coordinator, config_entry, **sensor_data)
        for sensor_data in SENSORS
    ]

    sensors2 = [
        BuienalarmSensorEntity(coordinator, config_entry, description,
                               location_id=config_entry.data.get("location_id", "unknown"),
                               location_name=config_entry.data.get("location_name", "unknown"))
        for description in SENSOR_DESCRIPTIONS
    ]

    sensors3: list[SensorEntity] = [
        BuienalarmSensorEntity(coordinator, config_entry, description,
                               location_id=config_entry.data.get("location_id", "unknown"),
                               location_name=config_entry.data.get("location_name", "unknown"))
        for description in SENSOR_DESCRIPTIONS
    ]

    sensors4 = [
        BuienalarmSensor(coordinator, config_entry, description.name, description.native_unit_of_measurement,
                         description.icon, description.device_class, description.state_class, description.key)
        for description in SENSOR_DESCRIPTIONS
    ]

    sensors5: list[SensorEntity] = [
        BuienalarmTestSensor(coordinator, config_entry, description)
        for description in SENSOR_DESCRIPTIONS
    ]

    _LOGGER.debug("[SENSOR SETUP] Adding %d sensors", len(sensors1))
    async_add_entities(sensors1, update_before_add=False)  # sensors van de oude setup *werkt*
    # async_add_entities(sensors2, update_before_add=True)  # sensors van SENSOR_DESCRIPTIONS *raw Nowcast Message*
    # async_add_entities(sensors3, update_before_add=True)  # sensors van SENSOR_DESCRIPTIONS met SensorEntity
    # async_add_entities(sensors4, update_before_add=True)  # sensors van SENSOR_DESCRIPTIONS met BuienalarmSensor
    # async_add_entities(sensors5, update_before_add=True)  # sensors van SENSOR_DESCRIPTIONS met BuienalarmTestSensor
    _LOGGER.debug("[SENSOR SETUP] %d sensors added", len(sensors1))

    # await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # ValueError: Config entry Schagen (1ba2a3d11e3e38b8e768ad5ceb4df8bf) for buienalarm.sensor has already been setup!
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload config entry when options are changed."""
    await hass.config_entries.async_reload(config_entry.entry_id)


# class BuienalarmTestSensor(CoordinatorEntity[BuienalarmDataUpdateCoordinator], SensorEntity):
class BuienalarmTestSensor(BuienalarmEntity, SensorEntity):
    def __init__(
        self,
        coordinator: BuienalarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
        description: SensorEntityDescription,
    ):
        # super().__init__(coordinator)
        super().__init__(coordinator, config_entry, description.key)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{config_entry.entry_id}-{description.key}"

    # @property
    # def strict_native_value(self) -> int | float | str | datetime | None:
    #     """Return the value for the sensor."""
    #     return self.coordinator.data.get(self.entity_description.key)

    @property
    def native_value(self) -> object:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            _LOGGER.debug("[TEST SENSOR] No data available for %s", self.entity_description.key)
            return None
        # return self.coordinator.data.get(self.entity_description.key)
        value = self.get_data(self.entity_description.key)
        return value


class BuienalarmSensor(BuienalarmEntity, SensorEntity):
    _LOGGER.debug("[SENSOR SETUP] BuienalarmSensor created")

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: BuienalarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
        name: str,
        unit_of_measurement: str,
        icon: str,
        device_class: str,
        state_class: str,
        key: str,
    ) -> None:
        _LOGGER.debug("[SENSOR ENTITY] __init__ for %s", name)
        super().__init__(coordinator, config_entry, key)
        self.entry_name = config_entry.data.get(CONF_NAME, "no_name")
        self.entry_place = config_entry.data.get("place", None)
        self._name = name
        self._unit_of_measurement = unit_of_measurement
        self._icon = icon
        self._device_class = device_class
        self._state_class = state_class
        self._key = key
        _LOGGER.debug("[SENSOR ENTITY] Initialized sensor: %s", self.name)

    @property
    def available(self) -> bool:
        """Geeft aan of de sensor data heeft opgehaald."""
        if not self.coordinator.last_update_success:
            return False
        if not self.coordinator.data:
            return False
        if not isinstance(self.coordinator.data, dict):
            _LOGGER.debug(
                "[SENSOR ENTITY] Coordinator data is not a dict: %s",
                type(self.coordinator.data).__name__,
            )
            return False
        # if self.coordinator.data.get(self._key, None) is None:
        #     return False
        return True

    @property
    def new_available(self) -> bool:
        """Geeft aan of de sensor data heeft opgehaald."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.get(self._key) is not None
        )

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}-{self.name.lower().replace(' ', '_')}"

    @property
    def name(self) -> str:
        """Return the sensor name."""
        if self.entry_place:
            return f"{self._name} {self.entry_place}"
        return self._name

    # StateType = str | int | float | None
    @property
    def native_value(self) -> StateType:
        """Return the current value of the sensor."""
        # extra check to ensure data is available
        if not self.coordinator.last_update_success or self.coordinator.data is None:
            _LOGGER.debug("[SENSOR ENTITY] No data available for key: %s", self._key)
            return None  # STATE_UNAVAILABLE  # STATE_UNKNOWN  # of None
        value = self.get_data(self._key)
        _LOGGER.debug("[SENSOR ENTITY] native_value for %s: %s", self._key, value)

        # Validate the value to match allowed StateType
        if isinstance(value, (str, int, float)) or value is None:
            return value

        _LOGGER.warning(
            "[SENSOR ENTITY] Unexpected value type for key '%s': %s (%s)",
            self._key,
            value,
            type(value).__name__,
        )
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def state_class(self) -> str | None:
        """Return the state class of this entity, if any."""
        return self._state_class

    @property
    def device_class(self) -> str | None:
        """Return the device class of this entity, if any."""
        return self._device_class

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend, if any."""
        return self._icon

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return the state attributes."""
        return {
            "precipitation_data": self.data_points_as_list,
            "attribution": ATTR_ATTRIBUTION,
        }
