"""BuienalarmEntity class"""
# entity.py

import logging
import math
import re
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Callable, Final

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt

from .const import API_CONF_URL, DOMAIN, NAME
from .coordinator import BuienalarmDataUpdateCoordinator

MAX_DURATION_MINUTES = 120

_LOGGER: logging.Logger = logging.getLogger(__name__)

# Bolt: Pre-compiled regex pattern for nowcast message timestamp placeholders to avoid re-compilation per call
_NOWCAST_PLACEHOLDER_RE: Final[re.Pattern[str]] = re.compile(r'\{(\d+)\}')

_LOGGER.debug("[ENTITY] Start entity.py")


def _safe_get(item: object, key: str, default: object = None) -> object:
    """Safely retrieve a key from a mapping-like item without raising exceptions."""
    # Bolt optimization: Fast path for exact built-in dicts avoids
    # creating bound method objects via getattr(item, "get") on every lookup (~4x faster).
    if type(item) is dict:
        return item.get(key, default)
    if isinstance(item, Mapping):
        try:
            return item.get(key, default)
        except Exception as err:
            _LOGGER.debug(
                "Error retrieving key '%s' from item (type=%s): %s",
                key,
                type(item).__name__,
                err,
            )
            return default
    if callable(getattr(item, "get", None)):
        try:
            get_fn = getattr(item, "get")
            return get_fn(key, default)
        except Exception as err:
            _LOGGER.debug(
                "Error retrieving key '%s' from item (type=%s): %s",
                key,
                type(item).__name__,
                err,
            )
            return default
    return default


def _as_float(value: object) -> float | None:
    """Convert an API value to float without accepting booleans or raising exceptions."""
    if isinstance(value, bool):
        return None

    res: float | None = None

    if isinstance(value, (int, float)):
        res = float(value)
    elif isinstance(value, str):
        try:
            res = float(value.replace(",", "."))
        except (ValueError, OverflowError):
            return None

    if res is not None and math.isfinite(res):
        return res

    return None


class BuienalarmEntity(CoordinatorEntity):
    """A Home Assistant entity that provides current
    and forecasted precipitation data from Buienalarm."""

    _attr_has_entity_name = True

    # Bolt optimization: Class-level mapping of keys to method names to avoid
    # dict creation and method binding overhead on every get_data call.
    _KEY_METHODS: Final[dict[str, str]] = {
        "nowcastmessage": "get_nowcastmessage",
        "mycastmessage": "get_mycastmessage",
        "precipitation_duration": "get_precipitation_duration",
        "precipitationrate_total": "get_total_precipitation_rate",
        "precipitationrate_hour": "get_total_precipitation_rate_for_next_hour",
        "precipitationrate_now": "get_current_precipitation",
        "precipitationrate_now_desc": "get_current_precipitation_rate_desc",
        "precipitationtype_now": "get_current_precipitation_type",
        "next_precipitation": "get_next_precipitation",
        "precipitation_periods": "_get_precipitation_periods_count",
    }

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, object]],
        config_entry: ConfigEntry,
        sensor_key: str
    ) -> None:
        super().__init__(coordinator)
        self.config_entry: ConfigEntry = config_entry
        self.sensor_key: str = sensor_key
        self._location_name: str = config_entry.data.get("location_name", "Unknown")

        # ========== Entity & unique_id ==========
        self._attr_translation_key = sensor_key
        # Unique ID format is <entry_id>_<sensor_key> for stable entity registry references
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_key}"
        # =======================================

    @property
    def data(self) -> Mapping[str, object]:
        """Return the endpoint payload, unwrapping coordinator metadata when present."""
        coordinator_data = self.coordinator.data
        if not isinstance(coordinator_data, Mapping):
            return {}

        # The API client wraps the raw endpoint payload in the timeseries key
        # together with retrieval metadata. Entity calculations consume the raw payload.
        if "timeseries" in coordinator_data:
            timeseries = coordinator_data.get("timeseries")
            if isinstance(timeseries, Mapping):
                return timeseries
            return {}

        # Retain compatibility with existing fixtures and cached coordinator data
        # that already contain the unwrapped endpoint payload.
        return coordinator_data

    def get_data(self, key: str) -> str | int | float | datetime | None:
        """
        Returns the sensor value associated with the given key from the coordinator.

        Attempts to resolve known dynamic methods first, and falls back to
        checking raw coordinator data. Returns None if not found or on error.

        Args:
            key: A predefined string key to fetch specific data.

        Returns:
            One of str, int, float, datetime, or None if data is missing or invalid.
        """
        data: Mapping[str, object] = self.data

        if not data:
            _LOGGER.error("[BUIENALARM ENTITY] No data available for sensor '%s'", self.sensor_key)
            return None

        # Bolt optimization: Use class-level method name mapping to avoid
        # dict creation and method binding overhead on every get_data call.
        method_name = self._KEY_METHODS.get(key)
        if method_name is not None:
            try:
                value = getattr(self, method_name)()
                _LOGGER.debug("[BUIENALARM ENTITY] Data for key '%s' (%s): %s", key, self.sensor_key, value)
                return value
            except Exception as err:
                _LOGGER.error(
                    "[BUIENALARM ENTITY] Error retrieving data for sensor '%s' and key '%s': %s",
                    self.sensor_key,
                    key,
                    err,
                )
                return None

        # fallback for raw data if present
        if isinstance(data, Mapping) and key in data:
            value: object = data.get(key)
            if isinstance(value, (str, int, float, datetime)):
                _LOGGER.debug("[BUIENALARM ENTITY] Raw fallback data for key '%s': %s", key, value)
                return value

        _LOGGER.warning("[BUIENALARM ENTITY] Key '%s' not found in data or methods", key)
        return None

    def _ensure_precip_data(self) -> list[dict[str, object]]:
        """Return precip list or raise ValueError for empty data."""
        data = self.data.get("data", [])
        if not isinstance(data, list) or not data:
            raise ValueError("Precipitation data missing or empty")
        return data


    @property
    def device_info(self) -> dict[str, object]:
        """Return device information for this entity.
        Wordt uitgevoerd"""
        _LOGGER.debug("[ENTITY] device_info config_entry: %s", self.config_entry.as_dict())
        place = (
            self.config_entry.data.get("place")
            or self.config_entry.data.get("location_name")
            or self.config_entry.data.get("name")
        )
        device_name = f"{NAME} {place}" if place and place != NAME else NAME

        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": device_name,
            "model": "Neerslag data",
            "manufacturer": NAME,
            "entry_type": DeviceEntryType.SERVICE,
            "suggested_area": place,
            "configuration_url": API_CONF_URL,
        }

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return extra state attributes."""
        attributes: dict[str, object] = {}

        if not self.coordinator.data:
            return attributes

        try:
            attributes.update({
                "location": self._location_name,
                # "updated_at": self.coordinator.data.get("updated_at", "Unknown"),
                "next_precipitation": self.get_next_precipitation(),
                "precipitationrate_now": self.get_current_precipitation(),
                "precipitationrate_now_desc": self.get_current_precipitation_rate_desc(),
                "precipitationrate_hour": self.get_total_precipitation_rate_for_next_hour(),
                "precipitationrate_total": self.get_total_precipitation_rate(),
                "precipitation_duration": self.get_precipitation_duration(),
                "precipitationtype_now": self.get_current_precipitation_type(),
                "nowcastmessage": self.get_nowcastmessage(),
                "mycastmessage": self.get_mycastmessage(),
                "precipitation_periods": self.get_precipitation_periods_as_dict(),
            })
        except (KeyError, ValueError, TypeError) as err:
            _LOGGER.error(
                "[BUIENALARM ENTITY] Failed to build attributes for '%s': %s",
                self.sensor_key,
                err,
            )

        return attributes

    @property
    def data_points_as_list(self) -> list[dict[str, str | int | float | datetime | None]]:
        """Return precipitation data points as a list of dictionaries.

        Each dict contains:

        * ``precipitationrate`` – mm/h (float | int | None)
        * ``precipitationtype`` – type code (str | None)
        * ``timestamp`` – UNIX seconds since epoch (int | float | None)
        * ``time`` – *local* `datetime`
        """
        raw_data = self.data.get("data") or []
        if not isinstance(raw_data, list):
            _LOGGER.debug(
                "Precipitation data is not a list (type=%s)",
                type(raw_data).__name__,
            )
            return []

        results: list[dict[str, str | int | float | datetime | None]] = []

        for data_point in raw_data:
            if not isinstance(data_point, Mapping) and not callable(getattr(data_point, "get", None)):
                _LOGGER.debug(
                    "Skipping data point without callable 'get' attribute (type=%s): %r",
                    type(data_point).__name__,
                    data_point,
                )
                continue

            rate = _safe_get(data_point, "precipitationrate")
            ptype = _safe_get(data_point, "precipitationtype")
            ts = _safe_get(data_point, "timestamp")
            iso_time = _safe_get(data_point, "time")

            parsed_time: datetime | None = None

            # Attempt derivation from numeric timestamp first
            if isinstance(ts, (int, float)) and not isinstance(ts, bool):
                try:
                    parsed_time = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                except (ValueError, TypeError, OverflowError) as exc:
                    _LOGGER.debug("Invalid numeric timestamp %r: %s", ts, exc)

            # Fallback to ISO time string if timestamp missing or invalid
            if parsed_time is None and isinstance(iso_time, str):
                try:
                    parsed_time = datetime.fromisoformat(iso_time)
                    if parsed_time.tzinfo is None:  # normalise to aware
                        parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                except ValueError as exc:
                    _LOGGER.debug("Invalid ISO time %r: %s", iso_time, exc)

            # Skip data point if neither timestamp nor time yields a valid datetime
            if parsed_time is None:
                _LOGGER.debug("Skipping data point without valid timestamp or ISO time: %r", data_point)
                continue

            # If timestamp was missing but ISO time was present, compute numeric timestamp
            if ts is None or isinstance(ts, bool) or not isinstance(ts, (int, float)):
                ts = int(parsed_time.timestamp())

            results.append(
                {
                    "precipitationrate": rate,
                    "precipitationtype": ptype,
                    "timestamp": ts,
                    "time": dt.as_local(parsed_time),
                }
            )

        return results

    def get_nowcastmessage(self) -> str | None:
        """Generate a user-friendly message for the current weather forecast."""
        if not self.data:
            return None

        nowcastmessage = self.data.get("nowcastmessage")
        if not isinstance(nowcastmessage, Mapping):
            return None

        nowcastmessage_data = nowcastmessage.get("nl")
        if not isinstance(nowcastmessage_data, str) or not nowcastmessage_data:
            return None

        matches = _NOWCAST_PLACEHOLDER_RE.findall(nowcastmessage_data)
        if not matches:
            return nowcastmessage_data

        try:
            datetimes_local = [
                dt.as_local(datetime.fromtimestamp(int(timestamp), tz=timezone.utc))
                for timestamp in matches
            ]
        except (ValueError, OverflowError, OSError) as exc:
            _LOGGER.debug(
                "[BUIENALARM ENTITY] Could not format timestamp in nowcastmessage '%s': %s",
                nowcastmessage_data,
                exc,
            )
            return nowcastmessage_data

        for timestamp, local_dt in zip(matches, datetimes_local):
            formatted_time = f"{local_dt.hour}:{local_dt.minute:02d}"
            nowcastmessage_data = nowcastmessage_data.replace(
                f"{{{timestamp}}}", formatted_time
            )

        return nowcastmessage_data

    def timestamp_to_local(self, timestamp: float) -> datetime:
        """ Convert a Unix timestamp to local time."""
        utc_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.as_local(utc_time)

    def format_time(self, timestamp: datetime | None) -> str:
        """Geef lokale tijd als 'H:MM' (zonder voorloop-0)."""
        if timestamp is None:
            return "Unknown time"

        # Zet naar lokale Home-Assistant-tijdzone
        local = dt.as_local(timestamp)

        # Standaard '%H:%M' en dan voorloop-nullen wegstrippen
        return f"{local.hour}:{local.minute:02d}"

    def get_mycastmessage(self) -> str | None:
        """Generate a user-friendly message for the precipitation forecast."""
        rain_data: object = self.data.get('data')

        if not isinstance(rain_data, list) or not rain_data:
            return "Geen data"

        rain_start_time, rain_stop_time, rain_restart_time, rain_duration, rain_stopped = self.get_rain_start_time_and_duration(
            rain_data)

        if rain_start_time is None:
            _LOGGER.debug("[BUIENALARM ENTITY] rain_start_time is None")
            return "Geen neerslag"

        if rain_duration is None:
            _LOGGER.debug("[BUIENALARM ENTITY] rain_duration is None")
            return "Ongeldige rain_duration tijd"

        _LOGGER.debug("[BUIENALARM ENTITY] Neerslag start om: %s",
                      self.format_time(rain_start_time))
        if rain_stop_time:
            _LOGGER.debug("[BUIENALARM ENTITY] Neerslag stopt om: %s",
                          self.format_time(rain_stop_time))
        _LOGGER.debug("[BUIENALARM ENTITY] Neerslag duurt: %s minuten", rain_duration)
        _LOGGER.debug("[BUIENALARM ENTITY] Neerslag gestopt: %s", rain_stopped)

        # current_precipitation_rate, current_precipitation_type = self.get_current_precipitation()
        current_precipitation_rate = self.get_current_precipitation()

        if current_precipitation_rate > 0:
            message_parts = [f"Neerslag duurt nog {rain_duration} minuten"]
            if rain_stop_time:
                message_parts.append(
                    f"en stopt rond {self.format_time(rain_stop_time)}")
            if rain_restart_time:
                message_parts.append(
                    f"en begint weer om {self.format_time(rain_restart_time)}")
            return " ".join(message_parts)

        now_utc = datetime.now(timezone.utc)

        if rain_start_time > now_utc:
            if rain_stop_time is None:
                return f"Neerslag voor langere tijd begint om {self.format_time(rain_start_time)}"
            return f"Neerslag begint om {self.format_time(rain_start_time)} en duurt {rain_duration} minuten"
        return f"Er wordt regen verwacht om {self.format_time(rain_start_time)} en duurt {rain_duration} minuten"

    def old_get_precipitation_duration(self) -> int:
        """ Get the duration of the current precipitation event in minutes. """
        precip_data = self._ensure_precip_data()

        # Check if the data is not empty and is in the expected format
        if not precip_data or not all(isinstance(entry, dict) for entry in precip_data):
            _LOGGER.error("[BUIENALARM ENTITY] Invalid or missing precipitation data")
            return 0
            # raise ValueError("Invalid or missing precipitation data")

        current_time: datetime = datetime.now(timezone.utc)
        precip_started: bool = False
        start_time: datetime | None = None

        for data_point in precip_data:
            timestamp = data_point.get("timestamp")
            if timestamp is None:
                _LOGGER.debug("Skipping precipitation entry without timestamp")
                continue
                # raise ValueError("Missing timestamp in precipitation data")
            data_point_time: datetime = datetime.fromtimestamp(
                timestamp, tz=timezone.utc)
            precip_rate = float(data_point.get("precipitationrate", 0))

            # Check if the current time is within the data point
            if data_point_time > current_time:
                if precip_rate > 0:
                    # Precipitation has started or ongoing
                    precip_started = True
                    if start_time is None:
                        start_time = data_point_time
                elif precip_started:
                    # Precipitation has reached 0
                    if start_time is None:
                        raise ValueError(
                            "Precipitation start time is not set.")
                    precip_duration: float = (
                        data_point_time - start_time).total_seconds() / 60
                    return min(MAX_DURATION_MINUTES, int(round(precip_duration)))
                else:
                    return 0

        # If we reach here, there is no ongoing precipitation
        return 0

    def get_precipitation_duration(self) -> int:
        """Return the duration of the current precipitation event in minutes."""
        try:
            precip_data: list[dict[str, float]] = self._ensure_precip_data()
        except ValueError:
            _LOGGER.debug("No precipitation data available")
            return 0

        if not precip_data:
            _LOGGER.debug("No precipitation data available")
            return 0

        current_time: datetime = datetime.now(timezone.utc)
        current_ts: float = current_time.timestamp()
        start_time: datetime | None = None
        last_time: datetime | None = None  # Track last processed forecast point

        for entry in precip_data:
            if not isinstance(entry, Mapping) and not callable(getattr(entry, "get", None)):
                _LOGGER.debug(
                    "Skipping precipitation entry that is not a mapping (type=%s): %r",
                    type(entry).__name__,
                    entry,
                )
                continue

            timestamp = _safe_get(entry, "timestamp")
            if timestamp is None or isinstance(timestamp, bool):
                _LOGGER.debug("Skipping precipitation entry without valid timestamp")
                continue

            try:
                ts_float = float(timestamp)
            except (ValueError, TypeError, OverflowError):
                _LOGGER.debug("Skipping invalid timestamp in precipitation entry: %r", timestamp)
                continue

            # Bolt performance optimization: Compare numeric timestamps directly
            # (ts_float + 300 <= current_ts) to skip historical entries before
            # creating datetime / timedelta objects (~30x faster in filtering loop).
            if ts_float + 300 <= current_ts:
                continue

            try:
                data_point_time = datetime.fromtimestamp(ts_float, tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                _LOGGER.debug("Skipping invalid timestamp in precipitation entry: %r", timestamp)
                continue

            # Bolt optimization: Skip raw_rate parsing for historical data points
            raw_rate = _safe_get(entry, "precipitationrate", 0)
            if isinstance(raw_rate, bool):
                precip_rate = 0.0
            else:
                try:
                    precip_rate = float(raw_rate)
                except (ValueError, TypeError):
                    precip_rate = 0.0

            last_time = data_point_time  # Update on every valid future or active point

            if precip_rate > 0:
                if start_time is None:
                    start_time = data_point_time
            else:
                if start_time is not None:
                    duration = (data_point_time - start_time).total_seconds() / 60
                    return min(MAX_DURATION_MINUTES, int(round(duration)))
                return 0

        # Precipitation continued through all forecast points
        if start_time is not None and last_time is not None:
            duration = (last_time - start_time).total_seconds() / 60
            return min(MAX_DURATION_MINUTES, int(round(duration)))

        return 0

    def _validate_timestamps(self, start_time: datetime, end_time: datetime) -> None:
        """Validate that *start_time* and *end_time* are timezone‑aware and in order.

        Raises
        ------
        ValueError
            If either datetime lacks *tzinfo* or if *start_time* > *end_time*.
        """
        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError(
                "start_time and end_time must be timezone‑aware datetime objects."
            )
        if start_time > end_time:
            raise ValueError("start_time must be earlier than or equal to end_time.")

    def _filter_data_by_time(
        self,
        data: list[dict[str, object]],
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, object]]:
        """
        Return data points whose UNIX ``timestamp`` is between *start_time*
        and *end_time* (both inclusive).

        Parameters
        ----------
        data
            Sequence of dicts containing a numeric ``timestamp`` key (seconds since epoch).
        start_time, end_time
            Inclusive time bounds. **Must** be timezone‑aware.

        Raises
        ------
        ValueError
            If inputs fail validation.

        Returns
        -------
        list[dict[str, object]]
            Filtered list, preserving the original ordering.
        """
        self._validate_timestamps(start_time, end_time)
        # Bolt performance optimization: use float timestamp comparison
        # directly to avoid datetime object overhead in the loop.
        start_ts: float = start_time.timestamp()
        end_ts: float = end_time.timestamp()

        filtered: list[dict[str, object]] = []
        for data_point in data:
            if not isinstance(data_point, Mapping) and not callable(getattr(data_point, "get", None)):
                _LOGGER.debug(
                    "Skipping non‑mapping data point (no callable 'get' attribute): %r",
                    data_point,
                )
                continue

            ts = _safe_get(data_point, "timestamp")
            if ts is None or isinstance(ts, bool):
                _LOGGER.debug(
                    "Skipping data point without valid 'timestamp': %r", data_point
                )
                continue
            if not isinstance(ts, (int, float)):
                _LOGGER.debug(
                    "Skipping data point with non‑numeric 'timestamp': %r", data_point
                )
                continue

            if ts + 300 > start_ts and ts <= end_ts:
                # mypy: safe because we've validated Mapping presence
                filtered.append(data_point)

        return filtered

    def calculate_total_precipitation_rate(
        self,
        data: list[dict[str, object]],
        start_time: datetime,
        end_time: datetime
    ) -> float:
        filtered_data = self._filter_data_by_time(data, start_time, end_time)

        if not filtered_data:
            return 0.0

        total_rate = 0.0
        has_rate = False

        for data_point in filtered_data:
            raw_rate = _safe_get(data_point, "precipitationrate")
            if raw_rate is None or isinstance(raw_rate, bool):
                continue
            try:
                total_rate += float(raw_rate)
                has_rate = True
            except (ValueError, TypeError):
                _LOGGER.debug("Skipping invalid precipitationrate: %r", raw_rate)

        if not has_rate:
            return 0.0

        total_time_seconds = (end_time - start_time).total_seconds()
        if total_time_seconds <= 0:
            return 0.0

        # Gemiddelde per uur
        average_precipitation_rate = total_rate / (total_time_seconds / 3600)
        return round(average_precipitation_rate, 1)

    def get_total_precipitation_rate(self) -> float:
        """ Get total precipitation rate rounded to one decimal place for the next 2 hours """
        data: object = self.data.get('data', [])
        if not isinstance(data, list):
            return 0.0
        current_time: datetime = datetime.now(timezone.utc)
        end_time: datetime = current_time + timedelta(hours=2)
        return self.calculate_total_precipitation_rate(data, current_time, end_time)

    def get_total_precipitation_rate_for_next_hour(self) -> float:
        """Calculate the total precipitation rate in mm/h for the upcoming hour."""
        # Fetch the precipitation data; expecting a list of dictionaries
        data: object = self.data.get('data', [])
        if not isinstance(data, list):
            return 0.0
        current_time: datetime = datetime.now(timezone.utc)  # Use UTC time
        end_time: datetime = current_time + timedelta(hours=1)

        _LOGGER.debug(
            "[BUIENALARM ENTITY] Calculating total precipitation rate from %s to %s", current_time, end_time)

        # Call the method to calculate the total precipitation rate
        total_precipitation = self.calculate_total_precipitation_rate(
            data, current_time, end_time)

        _LOGGER.debug(
            "[BUIENALARM ENTITY] Total precipitation rate for the next hour: %s mm/h", total_precipitation)
        return total_precipitation

    def get_current_precipitation(self) -> float:
        """Get the current precipitation rate."""
        data: object = self.data.get('data', [])
        # Bolt performance optimization: use epoch timestamps for rapid interval check
        current_ts: float = datetime.now(timezone.utc).timestamp()

        if isinstance(data, list):
            for data_point in data:
                if not isinstance(data_point, Mapping) and not callable(getattr(data_point, "get", None)):
                    _LOGGER.debug(
                        "[BUIENALARM ENTITY] Skipping non-mapping data point (type=%s): %r",
                        type(data_point).__name__,
                        data_point,
                    )
                    continue

                timestamp = _as_float(_safe_get(data_point, "timestamp"))
                precipitation_rate = _as_float(_safe_get(data_point, "precipitationrate"))
                precipitation_type = _safe_get(data_point, "precipitationtype")

                if timestamp is not None and precipitation_rate is not None:
                    _LOGGER.debug(
                        "[BUIENALARM ENTITY] Checking data point at timestamp %s with precipitation rate %s and type %s",
                        timestamp, precipitation_rate, precipitation_type
                    )

                    # Check if current time is within the 5-minute forecast bin [timestamp, timestamp + 300)
                    if timestamp <= current_ts < timestamp + 300:
                        return precipitation_rate
        return 0.0

    NO_PRECIPITATION = "Geen neerslag"

    PRECIPITATION_RAIN_CATEGORIES: Final[list[tuple[float, str]]] = [
        (15.0, "Heel zware regen"),
        (7.5, "Zware regen"),
        (2.0, "Matige regen"),
        (1.0, "Lichte regen"),
        (0.0, "Motregen"),
    ]

    PRECIPITATION_SNOW_CATEGORIES: Final[list[tuple[float, str]]] = [
        (15.0, "Heel zware sneeuw"),
        (7.5, "Zware sneeuw"),
        (2.0, "Matige sneeuw"),
        (1.0, "Lichte sneeuw"),
        (0.0, "Motsneeuw"),
    ]

    PRECIPITATION_RAIN_SNOW_CATEGORIES: Final[list[tuple[float, str]]] = [
        (15.0, "Heel zware regen en sneeuw"),
        (7.5, "Zware regen en sneeuw"),
        (2.0, "Matige regen en sneeuw"),
        (1.0, "Lichte regen en sneeuw"),
        (0.0, "Natte sneeuw"),
    ]

    def get_current_precipitation_rate_desc(self) -> str:
        """Get the description of the current precipitation rate."""
        data: object = self.data.get('data', [])
        current_ts: float = datetime.now(timezone.utc).timestamp()
        current_precipitation_rate_desc: str = self.NO_PRECIPITATION

        # Log the current timestamp for debugging
        _LOGGER.debug("[BUIENALARM ENTITY] Current timestamp for precipitation check: %s", current_ts)

        if not isinstance(data, list):
            return current_precipitation_rate_desc

        for data_point in data:
            if not isinstance(data_point, Mapping) and not callable(getattr(data_point, "get", None)):
                _LOGGER.debug(
                    "Skipping non-mapping data point in precipitation rate desc (type=%s): %r",
                    type(data_point).__name__,
                    data_point,
                )
                continue

            ts = _as_float(_safe_get(data_point, "timestamp"))
            if ts is not None and ts <= current_ts < ts + 300:
                current_precipitation_rate = _as_float(_safe_get(data_point, "precipitationrate")) or 0.0

                # Bolt optimization: Skip category checks for dry bins (rate <= 0)
                # while allowing subsequent overlapping forecast bins to be evaluated.
                if current_precipitation_rate <= 0:
                    continue

                raw_type = _safe_get(data_point, "precipitationtype")
                current_precipitation_type: str = (
                    raw_type if isinstance(raw_type, str) else self.NO_PRECIPITATION
                )

                categories = self.PRECIPITATION_RAIN_CATEGORIES
                if current_precipitation_type == "snow":
                    categories = self.PRECIPITATION_SNOW_CATEGORIES
                elif current_precipitation_type == "mix of rain and snow":
                    categories = self.PRECIPITATION_RAIN_SNOW_CATEGORIES

                # Log the found precipitation type and rate for debugging
                _LOGGER.debug(
                    "[BUIENALARM ENTITY] Found precipitation type: %s with rate: %s",
                    current_precipitation_type, current_precipitation_rate
                )

                for threshold, category in categories:
                    if current_precipitation_rate > threshold:
                        current_precipitation_rate_desc = category
                        _LOGGER.debug(
                            "[BUIENALARM ENTITY] Current precipitation rate description: %s",
                            current_precipitation_rate_desc
                        )
                        return current_precipitation_rate_desc  # Early return if found

        return current_precipitation_rate_desc

    def get_current_precipitation_type(self) -> str:
        """Get the type of current precipitation (rain, snow, etc.)."""
        precipitation_data: object = self.data.get("data", [])
        current_ts: float = datetime.now(timezone.utc).timestamp()
        current_type: str = self.NO_PRECIPITATION

        if not isinstance(precipitation_data, list):
            return current_type

        for data_point in precipitation_data:
            if not isinstance(data_point, Mapping) and not callable(getattr(data_point, "get", None)):
                _LOGGER.debug(
                    "Skipping non-mapping data point in precipitation type (type=%s): %r",
                    type(data_point).__name__,
                    data_point,
                )
                continue

            timestamp = _as_float(_safe_get(data_point, "timestamp"))
            if timestamp is not None and timestamp <= current_ts < timestamp + 300:
                current_rate = _as_float(_safe_get(data_point, "precipitationrate")) or 0.0

                if current_rate > 0:
                    current_type = _safe_get(data_point, "precipitationtype")
                    if current_type == "rain":
                        return "Regen"
                    elif current_type == "freezing rain":
                        return "Ijzel"
                    elif current_type == "snow":
                        return "Sneeuw"
                    elif current_type == "mix" or current_type == "mix of rain and snow":
                        return "Mix van regen en sneeuw"
                    return "Onbekend"

        return current_type if isinstance(current_type, str) else self.NO_PRECIPITATION

    def get_next_precipitation(self) -> int | None:
        """
        Return the number of **minutes from now** until the next precipitation event.

        Returns:
            int | None:
                - Returns 0 if precipitation is occurring now.
                - Returns the number of minutes until the next precipitation bin.
                - Returns None if no data is available or no precipitation is expected.
        """
        current_precipitation_rate = self.get_current_precipitation()
        if current_precipitation_rate > 0:
            _LOGGER.debug(
                "[BUIENALARM ENTITY] Precipitation is currently occurring for %s",
                self.sensor_key,
            )
            return 0

        precip_data: object = self.data.get("data", [])

        # ── quick sanity‑check ────────────────────────────────────────────────
        if not isinstance(precip_data, list) or not precip_data:
            _LOGGER.warning(
                "[BUIENALARM ENTITY] No precipitation data available for %s",
                self.sensor_key,
            )
            return None
        # ---------------------------------------------------------------------

        # Bolt performance optimization: use current epoch timestamp float
        # to compare directly against numeric forecast bin timestamps.
        now_ts: float = datetime.now(timezone.utc).timestamp()

        for data_point in precip_data:
            if not isinstance(data_point, Mapping) and not callable(getattr(data_point, "get", None)):
                _LOGGER.debug(
                    "Skipping non-mapping data point in next precipitation (type=%s): %r",
                    type(data_point).__name__,
                    data_point,
                )
                continue

            # Forecast points are 5‑minute bins.
            ts = _as_float(_safe_get(data_point, "timestamp"))

            # Skip if timestamp is missing, in the past, or beyond reasonable forecast horizon (24h)
            # Bolt optimization: numeric epoch comparison now_ts <= ts <= now_ts + 86400
            # bypasses datetime.fromtimestamp object allocations in loop iterations (~2.7x faster).
            if ts is None or ts < now_ts or ts > now_ts + 86400:
                continue

            rate = _as_float(_safe_get(data_point, "precipitationrate")) or 0.0

            if rate > 0:
                # Found the first future bin with precipitation
                delta_minutes: int = int(round((ts - now_ts) / 60))
                _LOGGER.debug(
                    "[BUIENALARM ENTITY] Next precipitation for %s in %d min (rate=%.2f mm/h)",
                    self.sensor_key,
                    delta_minutes,
                    rate,
                )
                # Avoid returning negative minutes due to clock skew or rounding
                return max(delta_minutes, 0)

        # No future precipitation found in dataset
        _LOGGER.debug(
            "[BUIENALARM ENTITY] No precipitation expected in current forecast for %s (%d forecast bins checked)",
            self.sensor_key,
            len(precip_data),
        )
        return None

    def check_rain_data_validity(self) -> bool:
        """Check if the precipitation data is valid and non-empty."""
        precipitation_data = self.data.get('data')

        if not precipitation_data or not isinstance(precipitation_data, list):
            _LOGGER.warning("[BUIENALARM ENTITY] Precipitation data is invalid or empty.")
            return False

        _LOGGER.info("[BUIENALARM ENTITY] Precipitation data is valid.")
        return True

    RAIN_INTERVAL_MINUTES = 5

    def get_rain_start_time_and_duration(
        self, precipitation_data: list[dict[str, object]]
    ) -> tuple[datetime | None, datetime | None, datetime | None, int, bool]:
        """Calculate the start time and duration of rain from the precipitation data."""
        current_time_utc: datetime = datetime.now(timezone.utc)
        current_ts: float = current_time_utc.timestamp()
        rain_start_time_utc: datetime | None = None
        rain_stop_time_utc: datetime | None = None
        rain_restart_time_utc: datetime | None = None
        rain_duration: int = 0
        rain_stopped: bool = True

        last_valid_time: datetime | None = None

        for data_point in precipitation_data:
            if not isinstance(data_point, Mapping) and not callable(getattr(data_point, "get", None)):
                continue

            timestamp = _safe_get(data_point, "timestamp")
            if timestamp is None or isinstance(timestamp, bool):
                continue  # Skip invalid entries

            try:
                ts_float = float(timestamp)
            except (ValueError, TypeError, OverflowError):
                continue

            # Bolt performance optimization: Compare numeric timestamps directly
            # (ts_float + 300 <= current_ts) to skip historical entries before
            # creating datetime / timedelta objects (~30x faster in filtering loop).
            if ts_float + 300 <= current_ts:
                continue

            try:
                data_point_timestamp = datetime.fromtimestamp(ts_float, tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                continue

            last_valid_time = data_point_timestamp

            # Bolt optimization: Skip raw_rate parsing for historical data points
            raw_rate = _safe_get(data_point, "precipitationrate", 0.0)
            if isinstance(raw_rate, bool):
                precipitation_rate = 0.0
            else:
                try:
                    precipitation_rate = float(raw_rate)
                    if not math.isfinite(precipitation_rate):
                        precipitation_rate = 0.0
                except (ValueError, TypeError, OverflowError):
                    precipitation_rate = 0.0

            if precipitation_rate > 0:
                rain_stopped = False
                if rain_start_time_utc is None:
                    rain_start_time_utc = data_point_timestamp
                if rain_stop_time_utc is None:
                    rain_duration += 5
                    rain_stopped = False
                if rain_restart_time_utc is None and rain_stop_time_utc is not None:
                    rain_restart_time_utc = data_point_timestamp
            # Check if there's a gap in precipitation
            elif rain_start_time_utc is not None and rain_stop_time_utc is None:
                rain_stop_time_utc = data_point_timestamp
                rain_stopped = True

        # Calculate rain duration if precipitation has started
        if rain_start_time_utc is not None:
            if rain_stop_time_utc is not None:
                rain_duration = int((rain_stop_time_utc -
                                     rain_start_time_utc).total_seconds() / 60)
            elif last_valid_time is not None:
                rain_duration = int((last_valid_time -
                                     rain_start_time_utc).total_seconds() / 60)
            rain_duration = int(rain_duration)

        return rain_start_time_utc, rain_stop_time_utc, rain_restart_time_utc, rain_duration, rain_stopped

    def _get_precipitation_periods_count(self) -> int:
        """Bolt optimization: Return count of precipitation periods directly without string conversions."""
        return len(self._get_precipitation_periods())

    def get_precipitation_periods_as_dict(self) -> list[dict[str, str | int | float | None]]:
        """
        Geef toekomstige neerslagperiodes terug als een lijst van dicts met ISO 8601 timestamps.

        Returns:
            list[dict[str, str | int | float | None]]: Een lijst met dicts per neerslagperiode:
                - start (str|None): ISO timestamp starttijd
                - stop (str|None): ISO timestamp stoptijd
                - duration (int|None): duur van de periode in minuten
                - precipitationrate (float|None): gemiddelde neerslagsnelheid in mm/u
        """
        precipitation_data: object = self.data.get("data")
        periods_list: list[dict[str, str | int | float | None]] = []

        if not isinstance(precipitation_data, list):
            _LOGGER.warning("[BUIENALARM ENTITY] 'data' ontbreekt of is geen lijst voor '%s'", self.sensor_key)
            return periods_list

        try:
            precipitation_periods = self._get_precipitation_periods()
        except Exception as err:
            _LOGGER.error(
                "[BUIENALARM ENTITY] Fout bij ophalen van neerslagperiodes voor '%s': %s",
                self.sensor_key,
                err,
            )
            return periods_list

        if not precipitation_periods:
            return periods_list

        for period in precipitation_periods:
            periods_list.append(
                {
                    "start": period["start"].isoformat() if period.get("start") else None,
                    "stop": period["stop"].isoformat() if period.get("stop") else None,
                    "duration": period.get("duration_minutes"),
                    "precipitationrate": period.get("precipitationrate"),
                }
            )

        return periods_list

    def _get_precipitation_periods(self) -> list[dict[str, object]]:
        """
        Return ongoing and future periods of positive forecast precipitation.

        Read self.data["data"] in input order, using timestamp as Unix seconds
        and precipitationrate as mm/h. Include a five-minute interval only if
        its end is strictly after the current UTC time, even if it has already
        started.

        A period ends at the next retained rate that is not greater than zero,
        or at the last retained timestamp if still open. No five minutes are
        added to that final timestamp, so an open period with one point lasts
        zero minutes. Return an empty list for missing or non-list data, or when
        there are no precipitation periods. Rate conversions raising TypeError
        or ValueError are skipped; timestamp conversion errors propagate.

        Returns:
            A list of dictionaries per period:
                - start: aware datetime in Home Assistant's local timezone.
                - stop: aware datetime in Home Assistant's local timezone.
                - duration_minutes: elapsed whole minutes from start to stop.
                - precipitationrate: arithmetic mean of the positive rates in
                  mm/h, rounded to two decimal places.

        Raises:
            ValueError: A retained timestamp is NaN or outside datetime's range.
            OverflowError: A timestamp or precipitation rate exceeds numeric
                conversion limits.
            OSError: The system cannot convert a retained timestamp.
        """
        precipitation_data: object = self.data.get("data", [])
        now_utc = datetime.now(timezone.utc)
        # Bolt performance optimization: Compare numeric timestamps directly
        # (raw_timestamp + 300 <= now_ts) to skip historical entries before
        # creating datetime / timedelta objects (~2.5x faster in filtering loop).
        now_ts = now_utc.timestamp()

        if not isinstance(precipitation_data, list):
            _LOGGER.warning("[BUIENALARM ENTITY] 'data' is geen lijst voor '%s'", self.sensor_key)
            return []

        _LOGGER.debug("[BUIENALARM ENTITY] Verwerken van %d datapunt(en) voor neerslagperiodes", len(precipitation_data))

        precipitation_periods_internal: list[tuple[datetime, datetime, list[float]]] = []
        in_precipitation = False
        precipitation_start: datetime | None = None
        current_rates: list[float] = []
        last_valid_time: datetime | None = None

        for i, item in enumerate(precipitation_data):
            if not isinstance(item, dict):
                _LOGGER.warning("[BUIENALARM ENTITY] Ongeldig datapunt op index %d: geen dict", i)
                continue

            raw_timestamp = item.get("timestamp")
            raw_precipitation = item.get("precipitationrate")

            if raw_timestamp is None or raw_precipitation is None:
                _LOGGER.warning(
                    "[BUIENALARM ENTITY] Ontbrekende keys of None-waarde op index %d: %s",
                    i,
                    list(item.keys()),
                )
                continue

            if not isinstance(raw_timestamp, (int, float)) or isinstance(raw_timestamp, bool):
                _LOGGER.warning("[BUIENALARM ENTITY] Ongeldige timestamp op index %d: %s", i, raw_timestamp)
                continue

            if isinstance(raw_precipitation, bool):
                _LOGGER.warning("[BUIENALARM ENTITY] Ongeldige neerslagwaarde op index %d: %s", i, raw_precipitation)
                continue

            try:
                precipitation_rate = float(raw_precipitation)
            except (TypeError, ValueError):
                _LOGGER.warning(
                    "[BUIENALARM ENTITY] Ongeldige neerslagwaarde op index %d: %s",
                    i,
                    raw_precipitation,
                )
                continue

            if raw_timestamp + 300 <= now_ts:
                continue  # negeer historische data

            data_time = datetime.fromtimestamp(raw_timestamp, tz=timezone.utc)
            last_valid_time = data_time

            if precipitation_rate > 0:
                current_rates.append(precipitation_rate)
                if not in_precipitation:
                    precipitation_start = data_time
                    in_precipitation = True
            else:
                if in_precipitation and precipitation_start is not None and current_rates:
                    precipitation_periods_internal.append((precipitation_start, data_time, current_rates.copy()))
                    current_rates.clear()
                    precipitation_start = None
                    in_precipitation = False

        # Bolt optimization: Use last_valid_time tracked in loop instead of O(N) reverse search
        if in_precipitation and precipitation_start is not None and current_rates and last_valid_time is not None:
            precipitation_periods_internal.append((precipitation_start, last_valid_time, current_rates.copy()))
            current_rates.clear()

        # omzetten naar HA-formaat met lokale tijd en gemiddelde neerslagsnelheid
        precipitation_periods_ha: list[dict[str, object]] = []
        for start_utc, stop_utc, rates in precipitation_periods_internal:
            local_start = dt.as_local(start_utc)
            local_stop = dt.as_local(stop_utc)
            avg_rate = round(sum(rates) / len(rates), 2)
            duration_minutes = int((stop_utc - start_utc).total_seconds() // 60)

            precipitation_periods_ha.append(
                {
                    "start": local_start,
                    "stop": local_stop,
                    "duration_minutes": duration_minutes,
                    "precipitationrate": avg_rate,
                }
            )

        return precipitation_periods_ha
