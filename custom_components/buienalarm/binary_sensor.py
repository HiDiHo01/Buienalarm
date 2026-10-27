"""Binary sensors for Buienalarm rain detection."""

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Final, override

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import BuienalarmConfigEntry, BuienalarmDataUpdateCoordinator
from .entity import _as_float
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
        config_entry: BuienalarmConfigEntry,
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
        if periods is None or not self.coordinator.last_update_success:
            self._attr_available = False
            self._attr_is_on = None
            return

        current_ts = datetime.now(timezone.utc).timestamp()

        match self.entity_description.key:
            case "precipitation_expected":
                self._attr_available = any(
                    _has_unexpired_period(period, current_ts) for period in periods
                )
                if not self._attr_available:
                    self._attr_is_on = None
                    return
                # Bolt optimization: short-circuit timestamp check before rate evaluation to skip historical points
                self._attr_is_on = any(
                    (_as_float(period.get("timestamp")) or 0.0) + 300 > current_ts
                    and _is_precipitation_period(period)
                    for period in periods
                )
            case "currently_raining":
                self._attr_available = any(
                    _has_active_period(period, current_ts) for period in periods
                )
                if not self._attr_available:
                    self._attr_is_on = None
                    return
                self._attr_is_on = any(
                    _is_current_precipitation_period(period, current_ts)
                    and _is_rain_period(period)
                    for period in periods
                )
            case "currently_snowing":
                self._attr_available = any(
                    _has_active_period(period, current_ts) for period in periods
                )
                if not self._attr_available:
                    self._attr_is_on = None
                    return
                self._attr_is_on = any(
                    _is_current_precipitation_period(period, current_ts)
                    and _is_snow_period(period)
                    for period in periods
                )
            case _:
                self._attr_available = False
                self._attr_is_on = None

    @property
    def icon(self) -> str | None:
        """Return dynamic icon when precipitation is active for improved UI clarity."""
        if self.is_on is True:
            if self.entity_description.key == "currently_snowing":
                return "mdi:weather-snowy"
            return "mdi:weather-pouring"
        return self.entity_description.icon


def _get_precipitation_periods(
    data: Mapping[str, object],
) -> list[Mapping[str, object]] | None:
    """Return validated precipitation periods from coordinator data."""
    raw_periods = data.get("data")
    if not isinstance(raw_periods, list):
        timeseries = data.get("timeseries")
        if isinstance(timeseries, Mapping):
            raw_periods = timeseries.get("data")

    if not isinstance(raw_periods, list):
        return None

    if not raw_periods:
        return []

    # Bolt performance optimization: Validate mappings, timestamps, and rates in a single-pass loop
    # to avoid multiple iterations and intermediate list allocations.
    periods: list[Mapping[str, object]] = []
    for period in raw_periods:
        if not isinstance(period, Mapping):
            return None
        if (
            _as_float(period.get("timestamp")) is None
            or _as_float(period.get("precipitationrate")) is None
        ):
            return None
        periods.append(period)

    return periods


def _is_precipitation_period(period: Mapping[str, object]) -> bool:
    """Return whether a precipitation period indicates precipitation."""
    precipitation_rate = _as_float(period.get("precipitationrate"))
    return precipitation_rate is not None and precipitation_rate > 0


def _is_rain_period(period: Mapping[str, object]) -> bool:
    """Return whether a period precipitation type matches rain types."""
    precipitation_type = period.get("precipitationtype")
    if not isinstance(precipitation_type, str):
        return False
    # Bolt optimization: fast path exact string match before fallback to .strip().lower() to avoid string allocations
    return (
        precipitation_type in _RAIN_TYPES
        or precipitation_type.strip().lower() in _RAIN_TYPES
    )


def _is_snow_period(period: Mapping[str, object]) -> bool:
    """Return whether a period precipitation type matches snow types."""
    precipitation_type = period.get("precipitationtype")
    if not isinstance(precipitation_type, str):
        return False
    # Bolt optimization: fast path exact string match before fallback to .strip().lower() to avoid string allocations
    return (
        precipitation_type in _SNOW_TYPES
        or precipitation_type.strip().lower() in _SNOW_TYPES
    )


def _has_active_period(
    period: Mapping[str, object],
    current_ts: float,
) -> bool:
    """Return whether a period covers the current 5-minute interval."""
    timestamp = _as_float(period.get("timestamp"))
    return timestamp is not None and timestamp <= current_ts < timestamp + 300


def _has_unexpired_period(
    period: Mapping[str, object],
    current_ts: float,
) -> bool:
    """Return whether a period is unexpired."""
    timestamp = _as_float(period.get("timestamp"))
    return timestamp is not None and timestamp + 300 > current_ts


def _is_current_precipitation_period(
    period: Mapping[str, object],
    current_ts: float,
) -> bool:
    """Return whether a period covers the current time and indicates precipitation."""
    return _has_active_period(period, current_ts) and _is_precipitation_period(period)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BuienalarmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Buienalarm binary sensors from their descriptions."""
    coordinator = getattr(config_entry, "runtime_data", None)
    if coordinator is None:
        raise RuntimeError(
            "Buienalarm coordinator is not available for config entry "
            f"{config_entry.entry_id}"
        )

    async_add_entities(
        BuienalarmBinarySensor(coordinator, config_entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )
