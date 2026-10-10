"""Sensor platform for the Buienalarm integration."""

import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import BuienalarmDataUpdateCoordinator
from .entity import BuienalarmEntity
from .sensor_types import SENSOR_DESCRIPTIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Buienalarm sensors from a config entry."""
    coordinator: BuienalarmDataUpdateCoordinator | None = getattr(
        config_entry, "runtime_data", None
    )
    if coordinator is None:
        coordinator = hass.data.get(DOMAIN, {}).get(config_entry.entry_id)

    if coordinator is None:
        _LOGGER.error(
            "Buienalarm coordinator unavailable for entry %s", config_entry.entry_id
        )
        return

    entities: list[SensorEntity] = [
        BuienalarmSensor(coordinator, config_entry, description)
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)


class BuienalarmSensor(BuienalarmEntity, SensorEntity):
    """Buienalarm sensor entity."""

    entity_description: SensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BuienalarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize a Buienalarm sensor."""
        super().__init__(coordinator, config_entry, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key or description.key

    @property
    def native_value(self) -> object:
        """Return native value of the sensor."""
        if not self.coordinator.last_update_success or self.coordinator.data is None:
            return None
        return self.get_data(self.entity_description.key)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success and self.coordinator.data is not None
        )
