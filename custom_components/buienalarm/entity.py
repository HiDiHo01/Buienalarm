"""BuienalarmEntity class"""
# entity.py

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from dateutil.tz import tzlocal
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt

from .const import API_CONF_URL, ATTRIBUTION, DOMAIN, NAME

_LOGGER: logging.Logger = logging.getLogger(__name__)

_LOGGER.debug("Start entity.py")


class BuienalarmEntity(CoordinatorEntity):
    """A Home Assistant entity that provides current and forecasted precipitation data from Buienalarm."""

    def __init__(self, coordinator, config_entry, sensor_key):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.sensor_key = sensor_key

    def get_data(self, key: str) -> str | int | float | datetime | None:
        """Returns data from the coordinator based on the given key."""
        data = self.coordinator.data
        # this method is called for every sensor
        # _LOGGER.debug("Data received: %s", data)
        _LOGGER.debug("Data received for sensor: %s", self.name)
        if data is None:
            _LOGGER.error("No Data for sensors")
            return None

        if key == 'nowcastmessage':
            # _LOGGER.debug("Data received: %s", self.get_nowcastmessage())
            return self.get_nowcastmessage()

        if key == 'mycastmessage':
            # _LOGGER.debug("Data received: %s", self.get_nowcastmessage())
            return self.get_mycastmessage()

        if key == 'precipitationrate_total':
            # _LOGGER.debug("Data received: %s", self.get_total_precipitation_rate())
            return self.get_total_precipitation_rate()

        if key == 'precipitationrate_hour':
            # _LOGGER.debug("Data received: %s", self.get_total_precipitation_rate_for_next_hour())
            return self.get_total_precipitation_rate_for_next_hour()

        if key == 'precipitationrate_now':
            # _LOGGER.debug("Data received: %s", self.get_current_precipitation_rate())
            return self.get_current_precipitation()

        if key == 'precipitationrate_now_desc':
            # _LOGGER.debug("Data received: %s", self.get_current_precipitation_rate_desc())
            return self.get_current_precipitation_rate_desc()

        if key == 'precipitationtype_now':
            # _LOGGER.debug("Data received: %s", self.get_current_precipitation_type())
            return self.get_current_precipitation_type()

        return data.get(key)

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}-{self.name.lower().replace(' ', '_')}"

    @property
    def device_info(self) -> dict:
        _LOGGER.debug("config_entry: %s", self.config_entry.as_dict())
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
    def extra_state_attributes(self) -> dict[str, Union[list[dict[str, Union[str, int]]], str]]:
        """Return the state attributes for the specific sensor."""
        if self.sensor_key == 'precipitationrate_total':
            return {
                "precipitation_data": self.data_points_as_list,
                "attribution": ATTRIBUTION,
            }
        else:
            return self.attribution

    @property
    def data_points_as_list(self) -> list[dict[str, Union[str, int, float]]]:
        """Return the precipitation data as a list of dictionaries."""
        data = self.coordinator.data.get('data', {})
        data_points = []
        for data_point in data:
            data_points.append({
                "precipitationrate": data_point.get('precipitationrate'),
                "precipitationtype": data_point.get('precipitationtype'),
                "timestamp": data_point.get('timestamp'),
                "time": dt.as_local(datetime.fromisoformat(data_point.get('time'))),
            })
        return data_points

    #def update(self):
    #    """Update the entity."""
    #    super().update()
    #    data = self.coordinator.data
    #    if data and "timestamp" in data:
    #        self.update_timestamp(int(data["timestamp"]))

    def get_nowcastmessage(self) -> Optional[str]:
        """Generate a user-friendly message for the current weather forecast."""
        nowcastmessage = self.coordinator.data.get('nowcastmessage')
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
                for i, timestamp in enumerate(matches):
                    formatted_time = datetimes_local[i].strftime("%H:%M")
                    if formatted_time.startswith('0'):
                        formatted_time = formatted_time[1:]  # Remove leading zero
                    nowcastmessage_data = nowcastmessage_data.replace(f'{{{timestamp}}}', formatted_time)

                # Return the modified input string
                return nowcastmessage_data
            return None

    def timestamp_to_local(self, timestamp):
        return dt.as_local(dt.utc_from_timestamp(timestamp))

    def format_time(self, timestamp: datetime) -> str:
        """ Function to format timestamps to a user-friendly string """
        if timestamp is None:
            return "Unknown time"

        # Convert timestamp to systems local time
        timestamp_local = timestamp.replace(tzinfo=timezone.utc).astimezone(tzlocal())

        # Get the configured timezone from Home Assistant
        # hass_timezone = self.hass.config.time_zone

        # Get the Home Assistant's configured timezone
        # hass_time_zone = dt.get_time_zone(self.hass)

        # Then, you can use it to convert your timestamp
        # timestamp_local = timestamp.replace(tzinfo=timezone.utc).astimezone(hass_time_zone)

        timestamp_str = timestamp_local.strftime("%H:%M")
        if timestamp_str.startswith('0'):
            timestamp_str = timestamp_str[1:]  # Remove leading zero
        return timestamp_str

    def get_mycastmessage(self) -> Optional[str]:
        """Generate a user-friendly message for the precipitation forecast."""
        rain_data: Optional[dict[str, Union[None, int, float, datetime]]] = self.coordinator.data.get('data')

        if rain_data is None:
            return "Geen data"

        rain_start_time, rain_stop_time, rain_restart_time, rain_duration, rain_stopped = self.get_rain_start_time_and_duration(rain_data)
        # return rain_start_time

        if rain_start_time is None:
            _LOGGER.debug("rain_start_time is None")
            return "Geen neerslag"

        if rain_stop_time is None:
            _LOGGER.debug("rain_stop_time is None")
            # return "Ongeldige stop tijd"
            # return "Regen voor langere tijd"

        if rain_duration is None:
            _LOGGER.debug("rain_duration is None")
            return "Ongeldige rain_duration tijd"

        _LOGGER.debug("Neerslag start om: %s", self.format_time(rain_start_time))
        _LOGGER.debug("Neerslag stopt om: %s", self.format_time(rain_stop_time))
        _LOGGER.debug("Neerslag duurt: %s minuten", rain_duration)
        _LOGGER.debug("Neerslag gestopt: %s", rain_stopped)

        # current_precipitation_rate, current_precipitation_type = self.get_current_precipitation()
        current_precipitation_rate = self.get_current_precipitation()

        if current_precipitation_rate > 0:
            message_parts = [f"Neerslag duurt nog {rain_duration} minuten"]
            if rain_stop_time:
                message_parts.append(f"en stopt rond {self.format_time(rain_stop_time)}")
            if rain_restart_time:
                message_parts.append(f"en begint weer om {self.format_time(rain_restart_time)}")
            return " ".join(message_parts)
        else:
            expected_rain_start = rain_start_time  # - timedelta(minutes=rain_duration)

            if expected_rain_start > datetime.utcnow():
                if rain_stop_time is None:
                    return f"Neerslag voor langere tijd begint om {self.format_time(rain_start_time)}"
                return f"Neerslag begint om {self.format_time(expected_rain_start)} en duurt {rain_duration} minuten"
            else:
                expected_rain_start_str = self.format_time(rain_start_time)
                return f"Er wordt regen verwacht om {expected_rain_start_str} en duurt {rain_duration} minuten"

    def filter_data_by_time(self, data: list[dict[str, any]], start_time: datetime, end_time: datetime) -> list[dict[str, any]]:
        return [
            data_point for data_point in data
            if start_time <= datetime.utcfromtimestamp(data_point.get("timestamp")) <= end_time
        ]

    def calculate_total_precipitation_rate(
        self, data: dict[str, any], start_time: datetime, end_time: datetime
    ) -> float:
        filtered_data = self.filter_data_by_time(data, start_time, end_time)

        if not filtered_data:
            return 0

        total_precipitation_rates = [
            data_point.get("precipitationrate", 0) for data_point in filtered_data
        ]

        total_time_period_seconds = (end_time - start_time).total_seconds()
        if total_time_period_seconds == 0:
            return 0

        total_precipitation_rate = sum(total_precipitation_rates) / (total_time_period_seconds / 3600)
        return round(total_precipitation_rate, 1)

    def get_total_precipitation_rate(self) -> float:
        """ Get total precipitation rate rounded to one decimal place for the next 2 hours """
        data: dict[str, Any] = self.coordinator.data.get('data', [])
        current_time: datetime = datetime.utcnow()
        end_time: datetime = current_time + timedelta(hours=2)
        return self.calculate_total_precipitation_rate(data, current_time, end_time)

    def get_total_precipitation_rate_for_next_hour(self) -> float:
        """ Calculate the total precipitation rate in mm/h for the upcoming hour """
        data: dict[str, Any] = self.coordinator.data.get('data', [])
        current_time: datetime = datetime.utcnow()
        end_time: datetime = current_time + timedelta(hours=1)
        return self.calculate_total_precipitation_rate(data, current_time, end_time)

    def get_current_precipitation(self) -> float:
        """Get the current precipitation rate."""
        data: dict[str, Any] = self.coordinator.data.get('data', [])
        current_time: datetime = datetime.utcnow()
        current_precipitation_rate: float = 0.0
        current_precipitation_type: str = '-'

        for data_point in data:
            data_point_timestamp = datetime.utcfromtimestamp(data_point.get("timestamp"))

            # Check if the current time is within the data point and the next 5 minutes
            if data_point_timestamp < current_time < data_point_timestamp + timedelta(minutes=5):
                current_precipitation_rate = float(data_point.get("precipitationrate", 0))
                current_precipitation_type = str(data_point.get("precipitationtype", "-"))

        return current_precipitation_rate  # , current_precipitation_type

    PRECIPITATION_CATEGORIES = [
        (15, "Heel zware regen"),
        (7.5, "Zware regen"),
        (2, "Matige regen"),
        (1, "Lichte regen"),
        (0, "Motregen"),
    ]

    NO_PRECIPITATION = "Geen neerslag"

    def get_current_precipitation_rate_desc(self) -> str:
        """Get the description of the current precipitation rate."""
        data: dict[str, Any] = self.coordinator.data.get('data', [])
        current_time: datetime = datetime.utcnow()
        current_precipitation_rate_desc: str = self.NO_PRECIPITATION

        for entry in data:
            entry_timestamp = datetime.utcfromtimestamp(entry.get("timestamp"))
            five_minutes_later = entry_timestamp + timedelta(minutes=5)

            if entry_timestamp < current_time < five_minutes_later:
                current_precipitation_rate = entry.get("precipitationrate", 0)

                for threshold, category in self.PRECIPITATION_CATEGORIES:
                    if current_precipitation_rate > threshold:
                        current_precipitation_rate_desc = category
                        break

        return current_precipitation_rate_desc

    def get_current_precipitation_type(self) -> str:
        """Get the type of current precipitation (rain, snow, etc.)."""
        precipitation_data = self.coordinator.data["data"]
        current_time = datetime.utcnow()
        current_type = self.NO_PRECIPITATION

        for data_point in precipitation_data:
            data_point_timestamp = datetime.utcfromtimestamp(data_point.get("timestamp"))
            five_minutes_later = data_point_timestamp + timedelta(minutes=5)
            if data_point_timestamp < current_time < five_minutes_later:
                current_rate = data_point.get("precipitationrate", 0)
                if current_rate > 0:
                    current_type = data_point.get("precipitationtype", "-")
                    if current_type == "rain":
                        current_type = "Regen"
                    elif current_type == "snow":
                        current_type = "Sneeuw"
        return current_type

    def check_rain_data_validity(self) -> bool:
        """Check if the precipitation data is valid and non-empty."""
        precipitation_data = self.coordinator.data.get('data')
        if precipitation_data is None or not precipitation_data:
            return False

        return True

    def old_get_rain_start_time_and_duration(self, precipitation_data):
        rain_start_time: datetime = None
        rain_stop_time: datetime = None
        rain_duration: int = 0
        consecutive_zero_precipitation: int = 0
        rain_stopped: bool = True

        for data_point in precipitation_data:
            precipitation_rate = data_point.get("precipitationrate", 0)

            if precipitation_rate > 0:
                if rain_start_time is None:
                    # set start time when there is precipitation and no start time
                    rain_start_time = datetime.utcfromtimestamp(data_point.get("timestamp"))
                    rain_stopped = False
                rain_duration += 5
                consecutive_zero_precipitation = 0
            else:
                consecutive_zero_precipitation += 5
                if rain_start_time is not None and rain_stop_time is None:  # and consecutive_zero_precipitation >= 10:
                    # set stop time when there is a start time and no stop time
                    rain_stop_time = data_point.get("timestamp")
                    rain_stopped = True
                    break  # Stop the loop when precipitation stops

        if rain_start_time is not None:
            rain_start_time = datetime.utcfromtimestamp(rain_start_time)
        if rain_stop_time is not None:
            rain_stop_time = datetime.utcfromtimestamp(rain_stop_time)

        return rain_start_time, rain_stop_time, rain_duration, rain_stopped

    def get_rain_start_time_and_duration(self, precipitation_data):
        """Calculate the start time and duration of rain from the precipitation data."""
        current_time_utc: datetime = datetime.utcnow()
        rain_start_time_utc: datetime = None
        rain_stop_time_utc: datetime = None
        rain_restart_time_utc: datetime = None
        rain_duration: int = 0
        rain_stopped: bool = True

        for data_point in precipitation_data:
            data_point_timestamp = datetime.utcfromtimestamp(data_point.get("timestamp"))
            precipitation_rate = data_point.get("precipitationrate", 0.0)

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
                rain_duration = (rain_stop_time_utc - rain_start_time_utc).total_seconds() / 60
            else:
                # Rain has started but no explicit stop time, use end of data time
                end_of_data_timestamp = precipitation_data[-1].get("timestamp")
                end_of_data_time = datetime.utcfromtimestamp(end_of_data_timestamp)
                rain_duration = (end_of_data_time - rain_start_time_utc).total_seconds() / 60
            rain_duration = int(rain_duration)

        return rain_start_time_utc, rain_stop_time_utc, rain_restart_time_utc, rain_duration, rain_stopped
