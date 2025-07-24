"""BuienalarmEntity class"""
# entity.py

import logging
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

from .const import API_CONF_URL, ATTR_ATTRIBUTION, DOMAIN, NAME
from .coordinator import BuienalarmDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__name__)

_LOGGER.debug("[ENTITY] Start entity.py")


class BuienalarmEntity(CoordinatorEntity):
    """A Home Assistant entity that provides current
    and forecasted precipitation data from Buienalarm."""

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

        # ========== Entity & unique‑id ==========
        # -> sensor.<prefix>_<key>
        self._attr_name = f"{NAME} {sensor_key}"
        # -> <config_entry.unique_id>_<key>   (falls back to entry‑id)
        base = config_entry.unique_id or config_entry.entry_id
        self._attr_unique_id = f"{base}_{sensor_key}"
        # =======================================

    @property
    def data(self) -> dict[str, object]:
        """Convenience property to access coordinator data."""
        return self.coordinator.data or {}

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
        data: dict[str, object] = self.coordinator.data

        if not data:
            _LOGGER.error("[BUIENALARM ENTITY] No data available for sensor '%s'", self.name)
            return None

        key_methods: Final[dict[str, Callable[[], str | int | float | datetime | dict[str, object] | None]]] = {
            'nowcastmessage': self.get_nowcastmessage,
            'mycastmessage': self.get_mycastmessage,
            'precipitation_duration': self.get_precipitation_duration,
            'precipitationrate_total': self.get_total_precipitation_rate,
            'precipitationrate_hour': self.get_total_precipitation_rate_for_next_hour,
            'precipitationrate_now': self.get_current_precipitation,
            'precipitationrate_now_desc': self.get_current_precipitation_rate_desc,
            'precipitationtype_now': self.get_current_precipitation_type,
            'next_precipitation': self.get_next_precipitation,
            # TODO: implement periods in atrributes
            "precipitation_periods": lambda: len(self.get_precipitation_periods_as_dict()),
            # 'precipitation_periods_as_list': self.get_precipitation_periods_as_list,
        }

        # Call the corresponding method if the key is in the defined methods
        if key in key_methods:
            try:
                value = key_methods[key]()
                _LOGGER.debug("[BUIENALARM ENTITY] Data for key '%s' (%s): %s", key, self.name, value)
                return value
            except Exception as err:
                _LOGGER.error(
                    "[BUIENALARM ENTITY] Error retrieving data for sensor '%s' and key '%s': %s",
                    self.name,
                    key,
                    err,
                )
                return None  # return None if an error occurs or not?

        # fallback for raw data if present
        if isinstance(data, dict) and key in data:
            value: object = data.get(key)
            if isinstance(value, (str, int, float, datetime)):
                _LOGGER.debug("[BUIENALARM ENTITY] Raw fallback data for key '%s': %s", key, value)
                return value

        _LOGGER.warning("[BUIENALARM ENTITY] Key '%s' not found in data or methods", key)
        return None

    def _ensure_precip_data(self) -> list[dict[str, object]]:
        """Return precip list or raise ValueError for empty data."""
        data = self.coordinator.data.get("data", [])
        if not isinstance(data, list) or not data:
            raise ValueError("Precipitation data missing or empty")
        return data

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}_{self.sensor_key}"

    @property
    def device_info(self) -> dict[str, object]:
        """Return device information for this entity.
        Wordt uitgevoerd"""
        _LOGGER.debug("[ENTITY] device_info config_entry: %s", self.config_entry.as_dict())
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": NAME,
            "model": "Neerslag data",
            "manufacturer": NAME,
            "entry_type": DeviceEntryType.SERVICE,
            "suggested_area": self.config_entry.data.get("place", None),
            "configuration_url": API_CONF_URL,
        }

    @property
    def old_extra_state_attributes(self) -> dict[str, list[dict[str, str | int | float | None]] | str]:
        """Return the state attributes for the specific sensor.
        """
        attributes = {"attribution": ATTR_ATTRIBUTION}

        if self.sensor_key == 'precipitationrate_total':
            attributes["precipitation_data"] = self.data_points_as_list

        return attributes

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
        except Exception as err:
            _LOGGER.error("[BUIENALARM ENTITY] Failed to build attributes for '%s': %s", self.name, err)

        return attributes

    @property
    def data_points_as_list(self) -> list[dict[str, str | int | float | None]]:
        """Return precipitation data points as a list of dictionaries.

        Each dict contains:

        * ``precipitationrate`` – mm/h (float | int | None)
        * ``precipitationtype`` – type code (str | None)
        * ``timestamp`` – UNIX seconds since epoch (int | float | None)
        * ``time`` – *local* `datetime`
        """
        raw_data: list[object] = []

        if isinstance(self.coordinator.data, Mapping):
            raw_data = self.coordinator.data.get("data") or []
        else:
            _LOGGER.debug(
                "coordinator.data is not a mapping (type=%s): %s",
                type(self.coordinator.data),
                self.coordinator.data,
            )

        results: list[dict[str, str | int | float | None]] = []

        for data_point in raw_data:
            # ── verify we can safely call .get() ────────────────────────────────
            if not isinstance(data_point, Mapping) and not hasattr(data_point, "get"):
                _LOGGER.debug(
                    "Skipping data point without 'get' attribute: %s",
                    data_point,
                )
                continue
            # -------------------------------------------------------------------

            rate = data_point.get("precipitationrate")
            ptype = data_point.get("precipitationtype")
            ts = data_point.get("timestamp")
            iso_time: str | None = data_point.get("time")

            # Parse ISO time string defensively
            parsed_time: datetime
            if isinstance(iso_time, str):
                try:
                    parsed_time = datetime.fromisoformat(iso_time)
                    if parsed_time.tzinfo is None:  # normalise to aware
                        parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                except ValueError as exc:
                    _LOGGER.debug("Invalid ISO time '%s': %s", iso_time, exc)
                    parsed_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
            else:
                parsed_time = datetime(1970, 1, 1, tzinfo=timezone.utc)

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
        nowcastmessage = self.coordinator.data.get('nowcastmessage')
        if nowcastmessage is None:
            return None

        if nowcastmessage is not None:
            nowcastmessage_data = nowcastmessage["nl"]
            if nowcastmessage_data:
                # Define a regular expression pattern to match timestamps within curly braces
                pattern = r'\{(\d+)\}'

                # Find all matches in the input string
                matches = re.findall(pattern, nowcastmessage_data)

                # Convert the found timestamps to datetime in local time
                datetimes_local = [
                    dt.as_local(dt.utc_from_timestamp(int(timestamp)))
                    for timestamp in matches
                ]

                # Replace the timestamp placeholders with formatted datetime strings
                for timestamp, local_dt in zip(matches, datetimes_local):
                    formatted_time = f"{local_dt.hour}:{local_dt.minute:02d}"  # Remove leading zero
                    nowcastmessage_data = nowcastmessage_data.replace(f"{{{timestamp}}}", formatted_time)

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
        rain_data: list[dict[str, int | float | datetime | None]] | None = self.coordinator.data.get('data')

        if not rain_data:
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

    def get_precipitation_duration(self) -> int:
        """ Get the duration of the current precipitation event in minutes. """
        # precip_data: list[dict[str, float]] = self.coordinator.data.get('data', [])
        precip_data = self._ensure_precip_data()

        # Check if the data is not empty and is in the expected format
        if not precip_data or not all(isinstance(entry, dict) for entry in precip_data):
            _LOGGER.error("[BUIENALARM ENTITY] Invalid or missing precipitation data")
            raise ValueError("Invalid or missing precipitation data")

        current_time: datetime = datetime.now(timezone.utc)
        precip_started: bool = False
        start_time: datetime | None = None

        for data_point in precip_data:
            timestamp = data_point.get("timestamp")
            if timestamp is None:
                raise ValueError("Missing timestamp in precipitation data")
            data_point_time: datetime = datetime.fromtimestamp(
                timestamp, tz=timezone.utc)
            precip_rate: float = data_point.get("precipitationrate", 0)

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
                    return int(round(precip_duration))
                else:
                    return 0

        # If we reach here, there is no ongoing precipitation
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
        start_utc: datetime = start_time.astimezone(timezone.utc)
        end_utc: datetime = end_time.astimezone(timezone.utc)

        filtered: list[dict[str, object]] = []
        for data_point in data:
            # ── NEW: verify the object is dict‑like ───────────────────────────────
            if not isinstance(data_point, Mapping) and not hasattr(data_point, "get"):
                _LOGGER.debug(
                    "Skipping non‑mapping data point (no 'get' attribute): %s",
                    data_point,
                )
                continue
            # ---------------------------------------------------------------------

            ts = data_point.get("timestamp")
            if ts is None:
                _LOGGER.debug(
                    "Skipping data point without 'timestamp': %s", data_point
                )
                continue
            if not isinstance(ts, (int, float)):
                _LOGGER.debug(
                    "Skipping data point with non‑numeric 'timestamp': %s", data_point
                )
                continue

            point_time: datetime = datetime.fromtimestamp(ts, tz=timezone.utc)
            if start_utc <= point_time <= end_utc:
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

        total_precipitation_rates = [
            data_point.get("precipitationrate", 0) for data_point in filtered_data
        ]

        total_time_seconds = (end_time - start_time).total_seconds()
        if total_time_seconds <= 0:
            return 0.0

        # Gemiddelde per uur
        average_precipitation_rate = sum(
            total_precipitation_rates) / (total_time_seconds / 3600)
        return round(average_precipitation_rate, 1)

    def get_total_precipitation_rate(self) -> float:
        """ Get total precipitation rate rounded to one decimal place for the next 2 hours """
        data: list[dict[str, object]] = self.coordinator.data.get('data', [])
        current_time: datetime = datetime.now(timezone.utc)
        end_time: datetime = current_time + timedelta(hours=2)
        return self.calculate_total_precipitation_rate(data, current_time, end_time)

    def get_total_precipitation_rate_for_next_hour(self) -> float:
        """Calculate the total precipitation rate in mm/h for the upcoming hour."""
        # Fetch the precipitation data; expecting a list of dictionaries
        data: list[dict[str, object]] = self.coordinator.data.get('data', [])
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
        data: list[dict[str, object]] = self.coordinator.data.get('data', [])
        current_time: datetime = datetime.now(timezone.utc)
        current_precipitation_rate: float = 0.0
        current_precipitation_type: str = '-'

        if data is not None:
            for data_point in data:
                timestamp = data_point.get("timestamp")
                precipitation_rate = data_point.get("precipitationrate")
                precipitation_type = data_point.get("precipitationtype")

                if timestamp is not None and precipitation_rate is not None and precipitation_type is not None:
                    if isinstance(data_point, dict):
                        data_point_timestamp = datetime.fromtimestamp(
                            timestamp, tz=timezone.utc)
                        _LOGGER.debug(
                            "[BUIENALARM ENTITY] Checking data point at %s with precipitation rate %s and type %s",
                            data_point_timestamp, precipitation_rate, precipitation_type
                        )
                    else:
                        _LOGGER.error(
                            "[BUIENALARM ENTITY] Data point is not a dictionary: %s", data_point)
                        continue

                    # Check if the current time is within the data point and the next 5 minutes
                    if data_point_timestamp < current_time < data_point_timestamp + timedelta(minutes=5):
                        current_precipitation_rate = float(precipitation_rate)
                        current_precipitation_type = str(precipitation_type)

                        return current_precipitation_rate  # , current_precipitation_type
        return current_precipitation_rate

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
        data: list[dict[str, object]] = self.coordinator.data.get('data', [])
        current_time: datetime = datetime.now(timezone.utc)
        current_precipitation_rate_desc: str = self.NO_PRECIPITATION

        # Log the current time for debugging
        _LOGGER.debug("[BUIENALARM ENTITY] Current time for precipitation check: %s", current_time)

        for data_point in data:
            data_point_timestamp = datetime.fromtimestamp(
                data_point.get("timestamp", 0), tz=timezone.utc)
            five_minutes_later = data_point_timestamp + timedelta(minutes=5)

            # Check if the current time is within the range of this data point
            if data_point_timestamp < current_time < five_minutes_later:
                current_precipitation_rate: float = data_point.get(
                    "precipitationrate", 0.0)
                current_precipitation_type: str = data_point.get(
                    "precipitationtype", self.NO_PRECIPITATION)

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
        precipitation_data: list[dict[str, object]] = self.coordinator.data.get("data", [])
        current_time: datetime = datetime.now(timezone.utc)
        current_type: str = self.NO_PRECIPITATION

        for data_point in precipitation_data:
            timestamp = data_point.get("timestamp", 0.0)
            data_point_timestamp: datetime = datetime.fromtimestamp(
                timestamp, tz=timezone.utc)
            five_minutes_later: datetime = data_point_timestamp + \
                timedelta(minutes=5)

            if data_point_timestamp < current_time < five_minutes_later:
                current_rate: float = data_point.get("precipitationrate", 0)
                if current_rate > 0:
                    current_type = data_point.get("precipitationtype", "-")
                    if current_type == "rain":
                        return "Regen"
                    elif current_type == "snow":
                        return "Sneeuw"
                    elif current_type == "mix of rain and snow":
                        return "Mix van regen en sneeuw"

        return current_type

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
                self.name,
            )
            return 0

        precip_data: list[dict[str, object]] = self.coordinator.data.get("data", [])

        # ── quick sanity‑check ────────────────────────────────────────────────
        if not precip_data:
            _LOGGER.warning(
                "[BUIENALARM ENTITY] No precipitation data available for %s",
                self.name,
            )
            return None
        # ---------------------------------------------------------------------

        now_utc: datetime = datetime.now(timezone.utc)

        for data_point in precip_data:
            # Forecast points are 5‑minute bins.
            ts_raw: object = data_point.get("timestamp")

            # Skip if timestamp is missing or malformed
            if not isinstance(ts_raw, (int, float)):
                _LOGGER.debug(
                    "[BUIENALARM ENTITY] Skipping invalid timestamp (type=%s) for %s: %s",
                    type(ts_raw).__name__,
                    self.name,
                    ts_raw,
                )
                continue

            try:
                ts: float = float(ts_raw)
            except (TypeError, ValueError):
                _LOGGER.debug(
                    "[BUIENALARM ENTITY] Skipping unparsable timestamp for %s: %s",
                    self.name,
                    ts_raw,
                )
                continue

            # Extract and validate precipitation rate
            raw_rate: object = data_point.get("precipitationrate", 0.0)

            if not isinstance(raw_rate, (int, float, str)):
                _LOGGER.debug(
                    "[BUIENALARM ENTITY] Skipping invalid precipitation rate (type=%s) for %s: %s",
                    type(raw_rate).__name__,
                    self.name,
                    raw_rate,
                )
                rate: float = 0.0
            else:
                try:
                    rate: float = float(raw_rate)
                except (TypeError, ValueError):
                    _LOGGER.debug(
                        "[BUIENALARM ENTITY] Failed to parse precipitation rate for %s: %s",
                        self.name,
                        raw_rate,
                    )
                    rate = 0.0

            point_time: datetime = datetime.fromtimestamp(ts, tz=timezone.utc)
            _LOGGER.debug(
                "[BUIENALARM ENTITY] Parsed timestamp for %s: %s",
                self.name,
                point_time.isoformat(),
            )

            # Ignore any point that lies in the past
            if point_time < now_utc:
                continue

            if rate > 0:
                # Found the first future bin with precipitation
                delta_minutes: int = int(round((point_time - now_utc).total_seconds() / 60))
                _LOGGER.debug(
                    "[BUIENALARM ENTITY] Next precipitation for %s in %d min (rate=%.2f mm/h)",
                    self.name,
                    delta_minutes,
                    rate,
                )
                # Avoid returning negative minutes due to clock skew or rounding
                return max(delta_minutes, 0)

        # No future precipitation found in dataset
        _LOGGER.debug(
            "[BUIENALARM ENTITY] No precipitation expected in current forecast for %s (%d forecast bins checked)",
            self.name,
            len(precip_data),
        )
        return None

    def check_rain_data_validity(self) -> bool:
        """Check if the precipitation data is valid and non-empty."""
        precipitation_data = self.coordinator.data.get('data')

        # Log the retrieved precipitation data for debugging purposes
        _LOGGER.debug("[BUIENALARM ENTITY] Retrieved precipitation data: %s", precipitation_data)

        if not precipitation_data:
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
        rain_start_time_utc: datetime | None = None
        rain_stop_time_utc: datetime | None = None
        rain_restart_time_utc: datetime | None = None
        rain_duration: int = 0
        rain_stopped: bool = True

        for data_point in precipitation_data:
            timestamp = data_point.get("timestamp")
            precipitation_rate = data_point.get("precipitationrate", 0.0)

            if timestamp is None:
                continue  # Skip invalid entries

            data_point_timestamp = datetime.fromtimestamp(timestamp,
                                                          tz=timezone.utc)

            # Check if there's precipitation at this data point and it's later than the current time
            if data_point_timestamp >= current_time_utc:
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
            else:
                # Rain has started but no explicit stop time, use end of data time
                end_of_data_timestamp = precipitation_data[-1].get("timestamp")
                if end_of_data_timestamp is not None:
                    end_of_data_time = datetime.fromtimestamp(
                        end_of_data_timestamp, tz=timezone.utc)
                    rain_duration = int((end_of_data_time -
                                         rain_start_time_utc).total_seconds()
                                        / 60)
            rain_duration = int(rain_duration)

        return rain_start_time_utc, rain_stop_time_utc, rain_restart_time_utc, rain_duration, rain_stopped

    def get_precipitation_periods_as_dict(self) -> list[dict[str, str | None]]:
        """
        Return precipitation periods as a list of dicts with ISO 8601 timestamps.

        Returns:
            A list of dicts with 'start' and 'stop' keys representing precipitation intervals.
            Timestamps are ISO formatted strings, or None if missing.
        """
        precipitation_data: object = self.coordinator.data.get("data")
        periods_list: list[dict[str, str | None]] = []

        if not isinstance(precipitation_data, list):
            _LOGGER.warning("[BUIENALARM ENTITY] 'data' missing or not a list for '%s'", self.name)
            return periods_list

        try:
            precipitation_periods = self._get_precipitation_periods()
        except Exception as err:
            _LOGGER.error("[BUIENALARM ENTITY] Failed to get precipitation periods for '%s': %s", self.name, err)
            return periods_list

        if not precipitation_periods:
            return None

        for period in precipitation_periods:
            periods_list.append({
                "start": period["start"].isoformat() if period["start"] else None,
                "stop": period["stop"].isoformat() if period["stop"] else None,
                "duration": int((period["stop"] - period["start"]).total_seconds() / 60) if period["start"] and period["stop"] else None,
                "precipitationrate": period["precipitationrate"],
            })

        return periods_list

    def _get_precipitation_periods(self) -> list[dict[str, object]]:
        """
        Bepaal neerslagperiodes op basis van neerslagdata.

        De data is een lijst van dicts met de keys:
        - 'timestamp': UNIX epoch in seconden (int of float)
        - 'precipitationrate': neerslagsnelheid in mm/u (float)

        Alleen toekomstige regen wordt meegenomen.
        Output is een lijst van dicts met:
        - start: lokale tijd (datetime)
        - stop: lokale tijd (datetime)
        - duration_minutes: duur in minuten (int)

        Args:
            precipitation_data: ruwe API data van buienalarm.

        Returns:
            Een lijst van dicts met regenperiodes.
        """
        precipitation_data: list[object] = self.coordinator.data.get("data", [])
        now_utc = datetime.now(timezone.utc)
        precipitation_periods_internal: list[tuple[datetime, datetime]] = []

        in_precipitation = False
        precipitation_start: datetime | None = None

        for i, item in enumerate(precipitation_data):
            if not isinstance(item, dict):
                _LOGGER.warning("[BUIENALARM ENTITY] Ongeldig datapunt op index %d: geen dict", i)
                continue

            raw_timestamp = item.get("timestamp")
            raw_precipitation = item.get("precipitationrate")

            if not isinstance(raw_timestamp, (int, float)):
                _LOGGER.warning("[BUIENALARM ENTITY] Ongeldige of ontbrekende timestamp op index %d", i)
                continue

            try:
                precipitation_rate = float(raw_precipitation)
            except (TypeError, ValueError):
                _LOGGER.warning("[BUIENALARM ENTITY] Ongeldige neerslagwaarde op index %d", i)
                precipitation_rate = 0.0

            data_time = datetime.fromtimestamp(raw_timestamp, tz=timezone.utc)

            if data_time < now_utc:
                continue  # negeer data uit verleden

            if precipitation_rate > 0:
                if not in_precipitation:
                    precipitation_start = data_time
                    in_precipitation = True
            else:
                if in_precipitation and precipitation_start is not None:
                    precipitation_stop = data_time
                    precipitation_periods_internal.append((precipitation_start, precipitation_stop))
                    precipitation_start = None
                    in_precipitation = False

        # Afsluiten laatste lopende bui
        if in_precipitation and precipitation_start is not None:
            last_valid = next(
                (d for d in reversed(precipitation_data)
                 if isinstance(d, dict) and isinstance(d.get("timestamp"), (int, float))),
                None,
            )
            if last_valid:
                last_time = datetime.fromtimestamp(last_valid["timestamp"], tz=timezone.utc)
                precipitation_periods_internal.append((precipitation_start, last_time))

        # Output in Home Assistant formaat (list[dict]), tijden in local timezone
        precipitation_periods_ha: list[dict[str, object]] = []
        for start_utc, stop_utc in precipitation_periods_internal:
            local_start = dt.as_local(start_utc)
            local_stop = dt.as_local(stop_utc)
            duration_minutes = int((stop_utc - start_utc).total_seconds() / 60)
            precipitation_periods_ha.append({
                "start": local_start,
                "stop": local_stop,
                "duration_minutes": duration_minutes,
            })

        return precipitation_periods_ha


class BuienalarmSensorEntity(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: BuienalarmDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
        location_id: str,
        location_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._name = description.name
        self.entity_description = description
        self._location_id = location_id
        self._key = description.key
        # self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_unique_id = f"{location_id}_{description.key}"
        self._location_name = location_name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "manufacturer": "Buienalarm",
            "name": entry.title,
            "model": "Neerslag data",
            "entry_type": DeviceEntryType.SERVICE,
            "configuration_url": "https://buienalarm.nl",
            "sw_version": "2025.7.20",
        }

    @property
    def native_value(self) -> str | int | float | None:
        """Return the state of the sensor."""
        if not self.coordinator.last_update_success:
            _LOGGER.debug(
                "[SENSOR ENTITY] Last update not successful for %s, returning None",
                self.name,
            )
            return None
        value = self.coordinator.data.get(self.entity_description.key)
        return value

    @property
    def old_available(self) -> bool:
        """
        Return True if the entity is available.

        The entity is considered available if the last data update was successful
        and the entity's key exists in the coordinator data.
        """
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.entity_description.key in self.coordinator.data
        )

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
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self._entry.entry_id}-{self.name.lower().replace(' ', '_')}"

    @property
    def name(self) -> str:
        """Return the sensor name."""
        # if self._entry.entry_place:
        #     return f"{self._name} {self._entry.entry_place}"
        return self._name

# testdata: dict[str, list[dict[str, object]] | dict[str, str]] = {"data": [{"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697945700, "time": "2023-10-22T03:35:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697946000, "time": "2023-10-22T03:40:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697946300, "time": "2023-10-22T03:45:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697946600, "time": "2023-10-22T03:50:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697946900, "time": "2023-10-22T03:55:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697947200, "time": "2023-10-22T04:00:00Z"}, {"precipitationrate": 0.1, "precipitationtype": "rain", "timestamp": 1697947500, "time": "2023-10-22T04:05:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697947800, "time": "2023-10-22T04:10:00Z"}, {"precipitationrate": 0.1, "precipitationtype": "rain", "timestamp": 1697948100, "time": "2023-10-22T04:15:00Z"}, {"precipitationrate": 0.2, "precipitationtype": "rain", "timestamp": 1697948400, "time": "2023-10-22T04:20:00Z"}, {"precipitationrate": 0.1, "precipitationtype": "rain", "timestamp": 1697948700, "time": "2023-10-22T04:25:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697949000, "time": "2023-10-22T04:30:00Z"}, {"precipitationrate": 0.1, "precipitationtype": "rain", "timestamp": 1697949300, "time": "2023-10-22T04:35:00Z"}, {
#     "precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697949600, "time": "2023-10-22T04:40:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697949900, "time": "2023-10-22T04:45:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697950200, "time": "2023-10-22T04:50:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697950500, "time": "2023-10-22T04:55:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697950800, "time": "2023-10-22T05:00:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697951100, "time": "2023-10-22T05:05:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697951400, "time": "2023-10-22T05:10:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697951700, "time": "2023-10-22T05:15:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697952000, "time": "2023-10-22T05:20:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697952300, "time": "2023-10-22T05:25:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697952600, "time": "2023-10-22T05:30:00Z"}, {"precipitationrate": 0, "precipitationtype": "rain", "timestamp": 1697952900, "time": "2023-10-22T05:35:00Z"}], "nowcastmessage": {"en": "Showers starting at {1697947500}, lasting 5 minutes", "de": "Niederschlag beginnt um {1697947500} und dauert 5 Minuten", "nl": "Neerslag begint om {1697947500} en duurt 5 minuten"}}
