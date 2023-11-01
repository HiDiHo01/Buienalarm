# sensor.py
import logging
from datetime import timedelta
from typing import Any, Optional

import requests
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)

from .const import API_ENDPOINT, DOMAIN, SENSORS
from .entity import BuienalarmEntity

# from .coordinator import BuienalarmDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__name__)


class BuienalarmDataUpdateCoordinator(DataUpdateCoordinator):
    _LOGGER.debug("BuienalarmDataUpdateCoordinator sensor.py")

    def __init__(self, hass, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.url = API_ENDPOINT.format(latitude, longitude)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5)  # set update interval
            )

    async def _async_update_data(self):
        try:
            response = await self.hass.async_add_executor_job(
                requests.get, self.url
                )
            response.raise_for_status()
            data = response.json()
            return data
        except (requests.RequestException, ValueError) as error:
            raise UpdateFailed(f"Error updating data: {error}") from error


async def async_setup_entry(hass, entry, async_add_devices):
    _LOGGER.debug("async_setup_entry sensor.py")
    coordinator = BuienalarmDataUpdateCoordinator(
        hass,
        entry.data["latitude"],
        entry.data["longitude"]
    )
    # Coordinator starts its data refresh
    await coordinator.async_config_entry_first_refresh()

    sensors = []

    for sensor_data in SENSORS:
        sensor = BuienalarmSensor(coordinator, entry, **sensor_data)
        sensors.append(sensor)

    async_add_devices(sensors)
    return True


class BuienalarmSensor(BuienalarmEntity, SensorEntity):
    _LOGGER.debug("BuienalarmSensor sensor.py")

    def __init__(
        self,
        coordinator,
        config_entry,
        name: str,
        unit_of_measurement: str,
        icon: str,
        device_class: str,
        state_class: str,
        attributes: list[dict[str, Any]],
        key: str,
    ) -> None:
        super().__init__(coordinator, config_entry, key)
        self.entry_name = config_entry.data.get(CONF_NAME, "no_name")
        self.entry_place = config_entry.data.get("place", None)
        self._name = name
        self._unit_of_measurement = unit_of_measurement
        self._icon = icon
        self._device_class = device_class
        self._state_class = state_class
        self._attributes = attributes
        self._key = key

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}-{self.name.lower().replace(' ', '_')}"

    @property
    def name(self) -> str:
        # return self._name
        return f"{self._name} {self.entry_place}"

    @property
    def native_value(self) -> Any:
        """Return the native_value of the sensor."""
        return self.get_data(self._key)

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def icon(self):
        return self._icon

#    @property
#    def device_state_attributes(self):
#        """Return additional attributes for the sensor."""
#        return {
#            "precipitation_data": self._coordinator.data.get("data", []),
#            ATTR_ATTRIBUTION: "Data provided by buienalarm.nl",
#        }

#    async def async_update(self):
#        _LOGGER.debug("async_update sensor.py")
#        """Update the sensor state by fetching the latest weather data."""
#        try:
#            await self.coordinator.async_request_refresh()
#            # Wait for the coordinator to fetch and update the data
#            await self.coordinator.async_wait_update()
#        except UpdateFailed as error:
#            _LOGGER.error(f"Error updating sensor data: {error}")
            # You can handle the error, such as setting the state to "Unavailable" or leaving it as is
