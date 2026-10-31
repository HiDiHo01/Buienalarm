# sensor.py
from collections.abc import Mapping
from datetime import datetime, timezone
import logging
import math
from typing import Final

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import ATTR_ATTRIBUTION, DOMAIN, SENSORS
from .coordinator import BuienalarmConfigEntry, BuienalarmDataUpdateCoordinator
from .entity import BuienalarmEntity, _as_float, _safe_get

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BuienalarmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Buienalarm sensors from config entry."""
    _LOGGER.debug(
        "[SENSOR SETUP] Setting up Buienalarm sensors for %s", config_entry.unique_id
    )

    coordinator: BuienalarmDataUpdateCoordinator | None = getattr(
        config_entry, "runtime_data", None
    ) or hass.data.get(DOMAIN, {}).get(config_entry.entry_id)
    if not coordinator:
        raise RuntimeError(
            "Buienalarm coordinator is not available for config entry "
            f"{config_entry.entry_id}"
        )

    sensors: list[SensorEntity] = [
        BuienalarmSensor(
            coordinator,
            config_entry,
            name=sensor_data["name"],
            unit_of_measurement=sensor_data["unit_of_measurement"],
            icon=sensor_data["icon"],
            device_class=sensor_data["device_class"],
            state_class=sensor_data["state_class"],
            key=sensor_data["key"],
            translation_key=sensor_data.get("translation_key", sensor_data["key"]),
            enabled_by_default=sensor_data.get("enabled_by_default", True),
        )
        for sensor_data in SENSORS
    ]

    _LOGGER.debug("[SENSOR SETUP] Adding %d sensors", len(sensors))
    async_add_entities(sensors, update_before_add=False)


class BuienalarmSensor(BuienalarmEntity, SensorEntity):
    """Represent a Buienalarm sensor entity."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: BuienalarmDataUpdateCoordinator,
        config_entry: BuienalarmConfigEntry,
        name: str,
        unit_of_measurement: str | None,
        icon: str | None,
        device_class: str | None,
        state_class: str | None,
        key: str,
        translation_key: str | None = None,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize the sensor."""
        _LOGGER.debug("[SENSOR ENTITY] __init__ for %s", key)
        super().__init__(coordinator, config_entry, key)
        self.entry_name = config_entry.data.get(CONF_NAME, "no_name")
        self.entry_place = (
            config_entry.data.get("place")
            or config_entry.data.get("location_name")
            or config_entry.data.get(CONF_NAME)
        )
        self._name = name
        self._unit_of_measurement = unit_of_measurement
        self._icon = icon
        self._device_class = device_class
        self._state_class = state_class
        self._key = key
        self._attr_translation_key = translation_key or key
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._attr_device_info = coordinator.device_info
        _LOGGER.debug(
            "[SENSOR ENTITY] Initialized sensor with translation key: %s",
            self._attr_translation_key,
        )

    @property
    def available(self) -> bool:
        """Return True if coordinator data and unwrapped forecast payload are available with valid fields."""
        if not self.coordinator.last_update_success:
            return False
        if not self.coordinator.data or not isinstance(self.coordinator.data, Mapping):
            _LOGGER.debug(
                "[SENSOR ENTITY] Coordinator data is not a Mapping or empty: %s",
                type(self.coordinator.data).__name__,
            )
            return False
        if not self.data or not isinstance(self.data, Mapping):
            _LOGGER.debug(
                "[SENSOR ENTITY] Unwrapped payload is not a Mapping or empty: %s",
                type(self.data).__name__,
            )
            return False

        if self._key == "nowcastmessage":
            nowcastmessage = self.data.get("nowcastmessage")
            if (
                not isinstance(nowcastmessage, Mapping)
                or not isinstance(nowcastmessage.get("nl"), str)
                or not nowcastmessage["nl"]
            ):
                _LOGGER.debug(
                    "[SENSOR ENTITY] Payload missing usable 'nowcastmessage.nl' for key %s",
                    self._key,
                )
                return False
        else:
            if not isinstance(self.data.get("data"), list):
                _LOGGER.debug(
                    "[SENSOR ENTITY] Payload missing 'data' list for key %s",
                    self._key,
                )
                return False

        if self._key == "mycastmessage":
            return self.get_rain_start_time_and_duration(self.data["data"]) is not None

        if self._key in (
            "precipitationrate_total",
            "precipitationrate_hour",
        ):
            current_ts = datetime.now(timezone.utc).timestamp()
            horizon = {
                "precipitationrate_hour": 3600,
                "precipitationrate_total": 7200,
            }.get(self._key)
            for point in self.data["data"]:
                timestamp = _as_float(_safe_get(point, "timestamp"))
                rate = _safe_get(point, "precipitationrate")
                if timestamp is None or isinstance(rate, bool):
                    continue
                try:
                    rate = float(rate)
                except (TypeError, ValueError, OverflowError):
                    continue
                if (
                    0 <= timestamp <= 253402300799
                    and current_ts < timestamp + 300
                    and (horizon is None or timestamp < current_ts + horizon)
                    and math.isfinite(rate)
                    and rate >= 0
                ):
                    return True
            return False

        if self._key in (
            "precipitationrate_now",
            "precipitationrate_now_desc",
            "precipitationtype_now",
        ):
            return self._get_current_data_point() is not None

        return True

    @property
    def native_value(self) -> StateType:
        """Return the current value of the sensor."""
        if not self.coordinator.last_update_success or self.coordinator.data is None:
            _LOGGER.debug("[SENSOR ENTITY] No data available for key: %s", self._key)
            return None
        value = self.get_data(self._key)
        _LOGGER.debug("[SENSOR ENTITY] native_value for %s: %s", self._key, value)

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
        if self._key in (
            "precipitationrate_now",
            "precipitationrate_hour",
            "precipitationrate_total",
        ):
            val = self.native_value
            if isinstance(val, (int, float)):
                return "mdi:weather-pouring" if val > 0 else "mdi:weather-sunny"
        elif self._key in ("next_precipitation", "precipitation_duration"):
            # Only interpret a zero/None state as dry with a valid forecast.
            forecast = self.data.get("data")
            if not isinstance(forecast, list) or not forecast:
                return self._icon
            now_ts = datetime.now(timezone.utc).timestamp()

            # Bolt performance optimization: Validate points and compute min/max timestamps
            # in a single pass over float values directly, avoiding double list traversal
            # and datetime object instantiations (~2.7x faster).
            min_ts = float("inf")
            max_ts = float("-inf")

            for point in forecast:
                if not isinstance(point, Mapping):
                    return self._icon
                ts = point.get("timestamp")
                rate = point.get("precipitationrate")
                if type(ts) is bool or not isinstance(ts, (int, float)):
                    return self._icon
                if type(rate) is bool or not isinstance(rate, (int, float)):
                    return self._icon
                ts_float = float(ts)
                rate_float = float(rate)
                if not (
                    math.isfinite(ts_float)
                    and math.isfinite(rate_float)
                    and rate_float >= 0
                    and 0 <= ts_float <= 253402300799
                ):
                    return self._icon
                if ts_float < min_ts:
                    min_ts = ts_float
                if ts_float > max_ts:
                    max_ts = ts_float

            # Forecast bins begin at five-minute boundaries and cover five minutes.
            if min_ts > now_ts or max_ts + 300 <= now_ts:
                return self._icon

            val = self.native_value
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                if self._key == "next_precipitation" and val is None:
                    return "mdi:weather-sunny"
                return self._icon
            if not math.isfinite(val) or val < 0:
                return self._icon
            if self._key == "next_precipitation":
                return "mdi:weather-pouring" if val == 0 else "mdi:clock-start"
            return "mdi:weather-pouring" if val > 0 else "mdi:weather-sunny"
        elif self._key in ("precipitationtype_now", "precipitationrate_now_desc"):
            val = self.native_value
            if isinstance(val, str):
                val_lower = val.lower()
                if "snow" in val_lower or "sneeuw" in val_lower:
                    return "mdi:weather-snowy"
                if any(k in val_lower for k in ("rain", "regen", "mix", "motregen")):
                    return "mdi:weather-pouring"
                if any(k in val_lower for k in ("geen", "none", "droog")):
                    # The text also defaults to dry when no current reading exists.
                    if self._get_current_data_point() is not None:
                        return "mdi:weather-sunny"
        return self._icon

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return additional state attributes for Home Assistant."""
        try:
            attributes = super().extra_state_attributes or {}
            if getattr(self.coordinator, "api_last_updated", None):
                attributes["api_last_updated"] = (
                    self.coordinator.api_last_updated.isoformat()
                )

            if self._key == "precipitationrate_total":
                attributes["precipitation_data"] = getattr(
                    self, "data_points_as_list", []
                )

            attributes["attribution"] = ATTR_ATTRIBUTION
            return attributes
        except Exception as exc:
            _LOGGER.error("Failed to build extra_state_attributes: %s", exc)
            return {}
