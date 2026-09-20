"""Binary sensors for Buienalarm rain detection."""

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Final, override

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BuienalarmDataUpdateCoordinator
from .sensor_types import BINARY_SENSOR_DESCRIPTIONS

_RAIN_TYPES: Final[frozenset[str]] = frozenset(
    {
        "rain",
        "freezing rain",
        "mix",
        "mix of rain and snow",
    }
)

_SNOW_TYPES: Final[frozenset[str]] = frozenset(
    {
        "snow",
        "wet snow",
        "mix",
        "mix of rain and snow",
    }
)


class BuienalarmBinarySensor(
    CoordinatorEntity[BuienalarmDataUpdateCoordinator],
    BinarySensorEntity,
):
    """Represent a Buienalarm rain-related binary sensor."""

    _attr_has_entity_name = True
    # entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: BuienalarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize a Buienalarm binary sensor."""
        CoordinatorEntity.__init__(self, coordinator)  # type: ignore[arg-type]
        self.entity_description = description
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info
        self._update_state()

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Update the entity when coordinator data changes."""
        self._update_state()
        super()._handle_coordinator_update()

    @callback
    def _update_state(self) -> None:
        """Update availability and state from the coordinator data."""
        data = self.coordinator.data
        if not isinstance(data, Mapping):
            self._attr_available = False
            self._attr_is_on = None
            return

        periods = _get_precipitation_periods(data)
        self._attr_available = (
            self.coordinator.last_update_success and periods is not None
        )

        if periods is None:
            self._attr_is_on = False
            return

        current_time = datetime.now(timezone.utc)

        match self.entity_description.key:
            case "precipitation_expected":
                self._attr_is_on = any(
                    _is_precipitation_period(period) for period in periods
                )
            case "currently_raining":
                self._attr_is_on = any(
                    _is_current_precipitation_period(period, current_time)
                    for period in periods if period.get("precipitationtype") in _RAIN_TYPES
                )
            case "currently_snowing":
                self._attr_is_on = any(
                    _is_current_precipitation_period(period, current_time)
                    for period in periods if period.get("precipitationtype") in _SNOW_TYPES
                )
            case _:
                self._attr_is_on = False


def _get_precipitation_periods(
    data: Mapping[str, object],
) -> list[Mapping[str, object]] | None:
    """Return validated precipitation periods from coordinator data."""
    raw_periods = data.get("data")
    if not isinstance(raw_periods, list) or not raw_periods:
        return None

    periods = [
        period
        for period in raw_periods
        if isinstance(period, Mapping)
    ]
    if len(periods) != len(raw_periods):
        return None

    return periods


def _is_precipitation_period(period: Mapping[str, object]) -> bool:
    """Return whether a precipitation period indicates precipitation."""
    precipitation_rate = _as_float(period.get("precipitationrate"))
    precipitation_type = period.get("precipitationtype")

    if precipitation_rate is None or precipitation_rate <= 0:
        return False

    if not isinstance(precipitation_type, str):
        return False

    return precipitation_type.strip().lower() in _RAIN_TYPES or precipitation_type.strip().lower() in _SNOW_TYPES


def _is_current_precipitation_period(
    period: Mapping[str, object],
    current_time: datetime,
) -> bool:
    """Return whether a period covers the current time and indicates precipitation."""
    timestamp = _as_float(period.get("timestamp"))
    if timestamp is None:
        return False

    period_start = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    period_end = period_start + timedelta(minutes=5)

    return (
        period_start <= current_time < period_end
        and _is_precipitation_period(period)
    )


def _as_float(value: object) -> float | None:
    """Convert an API value to float without raising an exception."""
    if isinstance(value, bool):
        return None

    if isinstance(value, int | float):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None

    return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Buienalarm binary sensors from their descriptions."""
    coordinator = hass.data.get(DOMAIN, {}).get(config_entry.entry_id)
    if not isinstance(coordinator, BuienalarmDataUpdateCoordinator):
        raise RuntimeError(
            "Buienalarm coordinator is not available for config entry "
            f"{config_entry.entry_id}"
        )

    async_add_entities(
        BuienalarmBinarySensor(coordinator, config_entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )
