"""Buienalarm base entity definition."""

import logging
import re
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Callable, Final

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTR_ATTRIBUTION, DOMAIN, NAME
from .coordinator import BuienalarmDataUpdateCoordinator

MAX_DURATION_MINUTES = 120

_LOGGER: logging.Logger = logging.getLogger(__name__)


class BuienalarmEntity(CoordinatorEntity[BuienalarmDataUpdateCoordinator]):
    """Base entity for Buienalarm entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BuienalarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_key: str,
    ) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self.config_entry: ConfigEntry = config_entry
        self.sensor_key: str = sensor_key
        self._location_name: str = config_entry.data.get("location_name", "Unknown")

        base_id = config_entry.unique_id or config_entry.entry_id
        self._attr_unique_id = f"{base_id}_{sensor_key}"
        self._attr_device_info: DeviceInfo = coordinator.device_info

    @property
    def unique_id(self) -> str:
        """Return unique ID for this entity."""
        base_id = self.config_entry.unique_id or self.config_entry.entry_id
        return f"{base_id}_{self.sensor_key}"

    @property
    def data(self) -> dict[str, object]:
        """Return coordinator data."""
        return self.coordinator.data or {}

    def get_data(self, key: str) -> str | int | float | datetime | None:
        """Return state value associated with key from coordinator."""
        data = self.coordinator.data
        if not data:
            _LOGGER.debug("No data available for entity '%s'", self.name)
            return None

        key_methods: Final[
            dict[
                str,
                Callable[[], str | int | float | datetime | dict[str, object] | None],
            ]
        ] = {
            "nowcastmessage": self.get_nowcastmessage,
            "mycastmessage": self.get_mycastmessage,
            "precipitation_duration": self.get_precipitation_duration,
            "precipitationrate_total": self.get_total_precipitation_rate,
            "precipitationrate_hour": self.get_total_precipitation_rate_for_next_hour,
            "precipitationrate_now": self.get_current_precipitation,
            "precipitationrate_now_desc": self.get_current_precipitation_rate_desc,
            "precipitationtype_now": self.get_current_precipitation_type,
            "next_precipitation": self.get_next_precipitation,
            "precipitation_periods": lambda: (
                len(self.get_precipitation_periods_as_dict())
                if self.get_precipitation_periods_as_dict()
                else 0
            ),
        }

        if key in key_methods:
            try:
                return key_methods[key]()
            except Exception as err:
                _LOGGER.error(
                    "Error retrieving data for key '%s' on '%s': %s",
                    key,
                    self.name,
                    err,
                )
                return None

        if isinstance(data, dict) and key in data:
            val = data.get(key)
            if isinstance(val, (str, int, float, datetime)):
                return val

        return None

    def _ensure_precip_data(self) -> list[dict[str, object]]:
        """Return precipitation forecast array or empty list."""
        data = self.coordinator.data.get("data", []) if self.coordinator.data else []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return extra state attributes."""
        attributes: dict[str, object] = {
            "attribution": ATTR_ATTRIBUTION,
        }

        if not self.coordinator.data:
            return attributes

        if getattr(self.coordinator, "api_last_updated", None):
            attributes["api_last_updated"] = (
                self.coordinator.api_last_updated.isoformat()
            )

        if self.sensor_key == "precipitationrate_total":
            attributes["precipitation_data"] = self.data_points_as_list

        return attributes

    @property
    def data_points_as_list(self) -> list[dict[str, str | int | float | None]]:
        """Return precipitation data points as a list of dicts."""
        raw_data: list[object] = []
        if isinstance(self.coordinator.data, Mapping):
            raw_data = self.coordinator.data.get("data") or []

        results: list[dict[str, str | int | float | None]] = []

        for data_point in raw_data:
            if not isinstance(data_point, Mapping):
                continue

            rate = data_point.get("precipitationrate")
            ptype = data_point.get("precipitationtype")
            ts = data_point.get("timestamp")
            iso_time: str | None = data_point.get("time")

            parsed_time: datetime
            if isinstance(iso_time, str):
                try:
                    parsed_time = datetime.fromisoformat(iso_time)
                    if parsed_time.tzinfo is None:
                        parsed_time = parsed_time.replace(tzinfo=timezone.utc)
                except ValueError:
                    parsed_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
            elif isinstance(ts, (int, float)):
                parsed_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                parsed_time = datetime(1970, 1, 1, tzinfo=timezone.utc)

            results.append(
                {
                    "precipitationrate": rate,
                    "precipitationtype": ptype,
                    "timestamp": ts,
                    "time": dt_util.as_local(parsed_time),
                }
            )

        return results

    def get_nowcastmessage(self) -> str | None:
        """Generate a user-friendly nowcast message."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return None

        nowcastmessage = self.coordinator.data.get("nowcastmessage")
        if nowcastmessage is None:
            return None

        if isinstance(nowcastmessage, str):
            return nowcastmessage

        if isinstance(nowcastmessage, dict):
            msg = nowcastmessage.get("nl") or nowcastmessage.get("en")
            if not isinstance(msg, str):
                return None

            pattern = r"\{(\d+)\}"
            matches = re.findall(pattern, msg)

            for timestamp in matches:
                try:
                    dt_obj = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                    local_dt = dt_util.as_local(dt_obj)
                    formatted_time = f"{local_dt.hour}:{local_dt.minute:02d}"
                    msg = msg.replace(f"{{{timestamp}}}", formatted_time)
                except (ValueError, OSError):
                    pass

            return msg

        return None

    def format_time(self, timestamp: datetime | None) -> str:
        """Format datetime as H:MM string."""
        if timestamp is None:
            return "Unknown time"
        local = dt_util.as_local(timestamp)
        return f"{local.hour}:{local.minute:02d}"

    def get_mycastmessage(self) -> str | None:
        """Generate a user-friendly custom message."""
        precip_data = self._ensure_precip_data()
        if not precip_data:
            return "Geen data"

        (
            rain_start_time,
            rain_stop_time,
            rain_restart_time,
            rain_duration,
            _,
        ) = self.get_rain_start_time_and_duration(precip_data)

        if rain_start_time is None:
            return "Geen neerslag"

        if rain_duration is None:
            return "Ongeldige rain_duration tijd"

        current_precipitation_rate = self.get_current_precipitation()

        if current_precipitation_rate > 0:
            message_parts = [f"Neerslag duurt nog {rain_duration} minuten"]
            if rain_stop_time:
                message_parts.append(
                    f"en stopt rond {self.format_time(rain_stop_time)}"
                )
            if rain_restart_time:
                message_parts.append(
                    f"en begint weer om {self.format_time(rain_restart_time)}"
                )
            return " ".join(message_parts)

        now_utc = datetime.now(timezone.utc)

        if rain_start_time > now_utc:
            if rain_stop_time is None:
                return f"Neerslag voor langere tijd begint om {self.format_time(rain_start_time)}"
            return f"Neerslag begint om {self.format_time(rain_start_time)} en duurt {rain_duration} minuten"
        return f"Er wordt regen verwacht om {self.format_time(rain_start_time)} en duurt {rain_duration} minuten"

    def get_precipitation_duration(self) -> int:
        """Return the duration of current or upcoming precipitation event in minutes."""
        precip_data = self._ensure_precip_data()
        if not precip_data:
            return 0

        current_time = datetime.now(timezone.utc)
        start_time: datetime | None = None
        last_time: datetime | None = None

        for entry in precip_data:
            timestamp = entry.get("timestamp")
            if timestamp is None or not isinstance(timestamp, (int, float)):
                continue

            data_point_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            precip_rate = float(entry.get("precipitationrate", 0))

            if data_point_time <= current_time:
                continue

            last_time = data_point_time

            if precip_rate > 0:
                if start_time is None:
                    start_time = data_point_time
            else:
                if start_time is not None:
                    duration = (data_point_time - start_time).total_seconds() / 60
                    return min(MAX_DURATION_MINUTES, int(round(duration)))
                return 0

        if start_time is not None and last_time is not None:
            duration = (last_time - start_time).total_seconds() / 60
            return min(MAX_DURATION_MINUTES, int(round(duration)))

        return 0

    def calculate_total_precipitation_rate(
        self, data: list[dict[str, object]], start_time: datetime, end_time: datetime
    ) -> float:
        """Calculate average precipitation rate (mm/h) between start and end time."""
        if not data:
            return 0.0

        start_utc = start_time.astimezone(timezone.utc)
        end_utc = end_time.astimezone(timezone.utc)
        total_time_seconds = (end_utc - start_utc).total_seconds()
        if total_time_seconds <= 0:
            return 0.0

        rates: list[float] = []
        for entry in data:
            if not isinstance(entry, Mapping):
                continue
            ts = entry.get("timestamp")
            if not isinstance(ts, (int, float)):
                continue
            pt_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            if start_utc <= pt_time <= end_utc:
                r = entry.get("precipitationrate", 0)
                if isinstance(r, (int, float)):
                    rates.append(float(r))

        if not rates:
            return 0.0

        avg_rate = sum(rates) / len(rates)
        return round(avg_rate, 1)

    def get_total_precipitation_rate(self) -> float:
        """Get total precipitation rate for next 2 hours."""
        precip_data = self._ensure_precip_data()
        current_time = datetime.now(timezone.utc)
        end_time = current_time + timedelta(hours=2)
        return self.calculate_total_precipitation_rate(
            precip_data, current_time, end_time
        )

    def get_total_precipitation_rate_for_next_hour(self) -> float:
        """Calculate total precipitation rate in mm/h for the upcoming hour."""
        precip_data = self._ensure_precip_data()
        current_time = datetime.now(timezone.utc)
        end_time = current_time + timedelta(hours=1)
        return self.calculate_total_precipitation_rate(
            precip_data, current_time, end_time
        )

    def get_current_precipitation(self) -> float:
        """Get the current precipitation rate."""
        precip_data = self._ensure_precip_data()
        current_time = datetime.now(timezone.utc)

        for data_point in precip_data:
            ts = data_point.get("timestamp")
            rate = data_point.get("precipitationrate")
            if isinstance(ts, (int, float)) and rate is not None:
                pt_time = datetime.fromtimestamp(ts, tz=timezone.utc)
                if pt_time <= current_time < pt_time + timedelta(minutes=5):
                    try:
                        return float(rate)
                    except (ValueError, TypeError):
                        return 0.0

        return 0.0

    NO_PRECIPITATION: Final[str] = "Geen neerslag"

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
        """Get description of current precipitation rate."""
        precip_data = self._ensure_precip_data()
        current_time = datetime.now(timezone.utc)

        for data_point in precip_data:
            ts = data_point.get("timestamp")
            if not isinstance(ts, (int, float)):
                continue

            pt_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            if pt_time <= current_time < pt_time + timedelta(minutes=5):
                rate = float(data_point.get("precipitationrate", 0.0))
                ptype = str(data_point.get("precipitationtype", self.NO_PRECIPITATION))

                categories = self.PRECIPITATION_RAIN_CATEGORIES
                if ptype == "snow":
                    categories = self.PRECIPITATION_SNOW_CATEGORIES
                elif ptype in ("mix", "mix of rain and snow"):
                    categories = self.PRECIPITATION_RAIN_SNOW_CATEGORIES

                for threshold, category in categories:
                    if rate > threshold:
                        return category

        return self.NO_PRECIPITATION

    def get_current_precipitation_type(self) -> str:
        """Get current precipitation type string."""
        precip_data = self._ensure_precip_data()
        current_time = datetime.now(timezone.utc)

        for data_point in precip_data:
            ts = data_point.get("timestamp")
            if not isinstance(ts, (int, float)):
                continue

            pt_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            if pt_time <= current_time < pt_time + timedelta(minutes=5):
                rate = float(data_point.get("precipitationrate", 0))
                if rate > 0:
                    current_type = str(data_point.get("precipitationtype", "-"))
                    if current_type == "rain":
                        return "Regen"
                    if current_type == "freezing rain":
                        return "Ijzel"
                    if current_type == "snow":
                        return "Sneeuw"
                    if current_type in ("mix", "mix of rain and snow"):
                        return "Mix van regen en sneeuw"

        return self.NO_PRECIPITATION

    def get_next_precipitation(self) -> int | None:
        """Return minutes until next precipitation event."""
        if self.get_current_precipitation() > 0:
            return 0

        precip_data = self._ensure_precip_data()
        if not precip_data:
            return None

        now_utc = datetime.now(timezone.utc)

        for data_point in precip_data:
            ts = data_point.get("timestamp")
            if not isinstance(ts, (int, float)):
                continue

            rate = float(data_point.get("precipitationrate", 0.0))
            point_time = datetime.fromtimestamp(ts, tz=timezone.utc)

            if point_time < now_utc:
                continue

            if rate > 0:
                delta_minutes = int(
                    round((point_time - now_utc).total_seconds() / 60)
                )
                return max(delta_minutes, 0)

        return None

    def get_rain_start_time_and_duration(
        self, precipitation_data: list[dict[str, object]]
    ) -> tuple[datetime | None, datetime | None, datetime | None, int, bool]:
        """Calculate start time, stop time, restart time, duration, and stopped status."""
        current_time_utc = datetime.now(timezone.utc)
        rain_start_time_utc: datetime | None = None
        rain_stop_time_utc: datetime | None = None
        rain_restart_time_utc: datetime | None = None
        rain_duration = 0
        rain_stopped = True

        for data_point in precipitation_data:
            ts = data_point.get("timestamp")
            rate = float(data_point.get("precipitationrate", 0.0))

            if not isinstance(ts, (int, float)):
                continue

            pt_time = datetime.fromtimestamp(ts, tz=timezone.utc)

            if pt_time >= current_time_utc:
                if rate > 0:
                    rain_stopped = False
                    if rain_start_time_utc is None:
                        rain_start_time_utc = pt_time
                    if rain_stop_time_utc is None:
                        rain_duration += 5
                    if (
                        rain_restart_time_utc is None
                        and rain_stop_time_utc is not None
                    ):
                        rain_restart_time_utc = pt_time
                elif rain_start_time_utc is not None and rain_stop_time_utc is None:
                    rain_stop_time_utc = pt_time
                    rain_stopped = True

        if rain_start_time_utc is not None:
            if rain_stop_time_utc is not None:
                rain_duration = int(
                    (rain_stop_time_utc - rain_start_time_utc).total_seconds() / 60
                )
            elif precipitation_data:
                last_ts = precipitation_data[-1].get("timestamp")
                if isinstance(last_ts, (int, float)):
                    end_time = datetime.fromtimestamp(last_ts, tz=timezone.utc)
                    rain_duration = int(
                        (end_time - rain_start_time_utc).total_seconds() / 60
                    )

        return (
            rain_start_time_utc,
            rain_stop_time_utc,
            rain_restart_time_utc,
            rain_duration,
            rain_stopped,
        )

    def get_precipitation_periods_as_dict(
        self,
    ) -> list[dict[str, str | int | float | None]]:
        """Return precipitation periods as list of dicts with ISO timestamps."""
        periods_list: list[dict[str, str | int | float | None]] = []
        precipitation_periods = self._get_precipitation_periods()

        for period in precipitation_periods:
            periods_list.append(
                {
                    "start": (
                        period["start"].isoformat()
                        if isinstance(period.get("start"), datetime)
                        else None
                    ),
                    "stop": (
                        period["stop"].isoformat()
                        if isinstance(period.get("stop"), datetime)
                        else None
                    ),
                    "duration": period.get("duration_minutes"),
                    "precipitationrate": period.get("precipitationrate"),
                }
            )

        return periods_list

    def _get_precipitation_periods(self) -> list[dict[str, object]]:
        """Determine future precipitation periods."""
        precip_data = self._ensure_precip_data()
        now_utc = datetime.now(timezone.utc)

        internal_periods: list[tuple[datetime, datetime, list[float]]] = []
        in_precipitation = False
        precipitation_start: datetime | None = None
        current_rates: list[float] = []

        for item in precip_data:
            ts = item.get("timestamp")
            rate_raw = item.get("precipitationrate")

            if not isinstance(ts, (int, float)) or rate_raw is None:
                continue

            try:
                rate = float(rate_raw)
            except (ValueError, TypeError):
                continue

            data_time = datetime.fromtimestamp(ts, tz=timezone.utc)
            if data_time < now_utc:
                continue

            if rate > 0:
                current_rates.append(rate)
                if not in_precipitation:
                    precipitation_start = data_time
                    in_precipitation = True
            else:
                if (
                    in_precipitation
                    and precipitation_start is not None
                    and current_rates
                ):
                    internal_periods.append(
                        (precipitation_start, data_time, current_rates.copy())
                    )
                    current_rates.clear()
                    precipitation_start = None
                    in_precipitation = False

        if in_precipitation and precipitation_start is not None and current_rates:
            last_ts = precip_data[-1].get("timestamp")
            if isinstance(last_ts, (int, float)):
                last_time = datetime.fromtimestamp(last_ts, tz=timezone.utc)
                internal_periods.append(
                    (precipitation_start, last_time, current_rates.copy())
                )

        ha_periods: list[dict[str, object]] = []
        for start_utc, stop_utc, rates in internal_periods:
            local_start = dt_util.as_local(start_utc)
            local_stop = dt_util.as_local(stop_utc)
            avg_rate = round(sum(rates) / len(rates), 2)
            duration_minutes = int((stop_utc - start_utc).total_seconds() // 60)

            ha_periods.append(
                {
                    "start": local_start,
                    "stop": local_stop,
                    "duration_minutes": duration_minutes,
                    "precipitationrate": avg_rate,
                }
            )

        return ha_periods
