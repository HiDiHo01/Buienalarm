"""BuienalarmEntity class"""
# entity.py

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt

from .const import API_CONF_URL, ATTRIBUTION, DOMAIN, NAME, VERSION

_LOGGER: logging.Logger = logging.getLogger(__name__)

_LOGGER.debug("Start entity.py")

NO_PRECIPITATION = "Geen neerslag"


class BuienalarmEntity(CoordinatorEntity):
    """A Home Assistant entity that provides current and forecasted precipitation data from Buienalarm."""

    def __init__(self, coordinator, config_entry, sensor_key):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = config_entry
        self.sensor_key = sensor_key

    def get_data(self, key: str) -> str | int | float | datetime | None:
        """Returns data from the coordinator based on the given key."""
        data = self.coordinator.data
        # this method is called for every sensor
        # _LOGGER.debug("Data received: %s", data)
        _LOGGER.debug("Data received for sensor: %s", self.name)
        if data is None:
            _LOGGER.error("Data for sensor is None")
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
    def old_extra_state_attributes(self) -> dict[str, Union[list[dict[str, Union[str, int]]], str]]:
        """Return the state attributes."""
        return {
            "precipitation_data": self.data_points_as_list,
            "attribution": ATTRIBUTION,
        }

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes for the specific sensor."""
        if self.sensor_key == 'precipitationrate_total':
            return {
                "precipitation_data": self.data_points_as_list,
                "attribution": ATTRIBUTION,
            }
        else:
            return {}

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
                "time": data_point.get('time')
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

    def _get_mycastmessage(self) -> Optional[str]:
        rain_data = self.coordinator.data.get('data')
        date_string = '2023-10-22T05:55:00Z'
        rain_start_time, rain_stop_time, rain_duration, rain_stopped = self.get_rain_start_time_and_duration(rain_data)
        if rain_start_time:
            date_string = rain_start_time
        datetime_object = datetime.fromisoformat(date_string)
        local_datetime_object = dt.as_local(datetime_object)
        datetime_object_str = local_datetime_object.strftime('%H:%M')
        return datetime_object_str[1:] if datetime_object_str.startswith('0') else datetime_object_str
        return datetime_object_str
        if rain_data is not None:
            rain_start_time, rain_stop_time, rain_duration, rain_stopped = self.get_rain_start_time_and_duration(rain_data)
            mycastmessage = "Geen neerslag"
            if rain_start_time:
                dt.as_utc(rain_start_time)
                utctime = rain_start_time.strftime("%Y-%m-%d %H:%M:%S") + "+0000"
                utc_dt = datetime.strptime(utctime, "%Y-%m-%d %H:%M:%S%z")
                local_dt = utc_dt.replace(tzinfo=timezone.utc).astimezone()
                return local_dt
                rain_start_time = dt.as_local(dt.utc_from_timestamp(int(rain_start_time.timestamp())))
                return rain_start_time
                rain_start_time_str = rain_start_time.strftime('%H:%M')
                if rain_start_time_str.startswith('0'):
                    rain_start_time_str = rain_start_time_str[1:]  # Remove leading zero
                if rain_stop_time is not None:
                    rain_stop_time = dt.as_local(dt.utc_from_timestamp(int(rain_stop_time.timestamp())))
                    rain_stop_time_str = rain_stop_time.strftime('%H:%M')
                    if rain_stop_time_str.startswith('0'):
                        rain_stop_time_str = rain_stop_time_str[1:]  # Remove leading zero
                    if rain_stopped:
                        mycastmessage = f"Neerslag begint om {rain_start_time_str} en duurt {rain_duration} minuten en stopt om {rain_stop_time_str}."
                    else:
                        mycastmessage = f"Neerslag begint om {rain_start_time_str} en duurt nog {rain_duration} minuten."
            return mycastmessage
        return None

    # Define a function to format timestamps to a user-friendly string
    def format_time(self, timestamp: Union[None, datetime]) -> str:
        if timestamp is None:
            return "Unknown time"

        # Convert rain_start_time to local time
        timestamp_utc = timestamp.strftime("%Y-%m-%d %H:%M:%S") + "+0000"
        timestamp_utc = datetime.strptime(timestamp_utc, "%Y-%m-%d %H:%M:%S%z")
        timestamp_local = timestamp_utc.replace(tzinfo=timezone.utc).astimezone()

        timestamp_str = timestamp_local.strftime("%H:%M")
        if timestamp_str.startswith('0'):
            timestamp_str = timestamp_str[1:]  # Remove leading zero
        return timestamp_str

    def get_mycastmessage(self) -> Optional[str]:
        """Generate a user-friendly message for the precipitation forecast."""
        rain_data: Optional[dict[str, Union[None, float, datetime]]] = self.coordinator.data.get('data')

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

        # current_precipitation_rate, current_precipitation_type = self.get_current_precipitation()
        current_precipitation_rate = self.get_current_precipitation()

        if current_precipitation_rate > 0:
            if not rain_stopped:
                precipitation_message = f"Neerslag duurt nog {rain_duration} minuten en stopt om {self.format_time(rain_stop_time)}"
                if rain_restart_time is not None:
                    precipitation_message += f" en begint weer om {self.format_time(rain_restart_time)}"
                return precipitation_message
            else:
                return f"Neerslag begint om {self.format_time(rain_start_time)} en duurt {rain_duration} minuten en stopt om {self.format_time(rain_stop_time)}"
        else:
            expected_rain_start = rain_start_time  # - timedelta(minutes=rain_duration)

            if expected_rain_start > datetime.utcnow():
                if rain_stop_time is None:
                    return f"Neerslag begint om {self.format_time(rain_start_time)}"
                return f"Neerslag begint om {self.format_time(expected_rain_start)} en duurt {rain_duration} minuten"
            else:
                expected_rain_start_str = self.format_time(rain_start_time)
                return f"Er wordt regen verwacht om {expected_rain_start_str} en duurt {rain_duration} minuten"

        return NO_PRECIPITATION

    def oldget_mycastmessage(self) -> Optional[str]:
        rain_data = self.coordinator.data.get('data')
        if rain_data is not None:
            rain_start_time, rain_stop_time, rain_duration, rain_stopped = self.get_rain_start_time_and_duration(rain_data)
            if rain_start_time is None:
                # return "Ongeldige start tijd"
                _LOGGER.debug("rain_start_time is None")
            else:
                _LOGGER.debug("Neerslag start om: %s", rain_start_time)
            if rain_stop_time is None:
                # return "Ongeldige stop tijd"
                _LOGGER.debug("rain_stop_time is None")
            else:
                _LOGGER.debug("Neerslag stopt om: %s", rain_stop_time)
            if rain_duration is None:
                # return "Ongeldige rain_duration tijd"
                _LOGGER.debug("rain_duration is None")
            else:
                _LOGGER.debug("Neerslag duurt: %s minuten", rain_duration)
            if rain_stopped is None:
                # return "Ongeldige rain_duration tijd"
                _LOGGER.debug("rain_stopped is None")
            else:
                _LOGGER.debug("Neerslag gestopt: %s", rain_stopped)
            # Check if it's currently raining
            if self.get_current_precipitation() > 0:
                # It's currently raining, return an appropriate message
                if rain_start_time:

                    # Convert rain_start_time to local time
                    rain_start_time_utc = rain_start_time.strftime("%Y-%m-%d %H:%M:%S") + "+0000"
                    rain_start_time_utc = datetime.strptime(rain_start_time_utc, "%Y-%m-%d %H:%M:%S%z")
                    rain_start_time_local = rain_start_time_utc.replace(tzinfo=timezone.utc).astimezone()
                    if rain_stop_time:
                        rain_stop_time_utc = rain_stop_time.strftime("%Y-%m-%d %H:%M:%S") + "+0000"
                        rain_stop_time_utc = datetime.strptime(rain_stop_time_utc, "%Y-%m-%d %H:%M:%S%z")
                        rain_stop_time_local = rain_stop_time_utc.replace(tzinfo=timezone.utc).astimezone()
                        rain_stop_time_str = rain_stop_time_local.strftime('%H:%M')
                        if rain_stop_time_str.startswith('0'):
                            rain_stop_time_str = rain_stop_time_str[1:]  # Remove leading zero

                    # Strip leading 0 if there is one
                    rain_start_time_str = rain_start_time_local.strftime('%H:%M')
                    if rain_start_time_str.startswith('0'):
                        rain_start_time_str = rain_start_time_str[1:]  # Remove leading zero

                    if not rain_stopped:
                        mycastmessage = f"Neerslag begon om {rain_start_time_str} en duurt {rain_duration} minuten"
                    else:
                        mycastmessage = f"Neerslag begint om {rain_start_time_str} en duurt {rain_duration} minuten en stopt om {rain_stop_time_str}"
                    return mycastmessage
            else:
                # It's not currently raining, but rain is expected
                if rain_start_time:
                    # Calculate when rain is expected to start
                    expected_rain_start = rain_start_time - timedelta(minutes=rain_duration)
                    if expected_rain_start > datetime.utcnow():
                        # expected_rain_start = dt.as_local(expected_rain_start)  # Convert expected_rain_start to local timezone

                        expected_rain_start_utc = expected_rain_start.strftime("%Y-%m-%d %H:%M:%S") + "+0000"
                        expected_rain_start_utc = datetime.strptime(expected_rain_start_utc, "%Y-%m-%d %H:%M:%S%z")
                        expected_rain_start_local = expected_rain_start_utc.replace(tzinfo=timezone.utc).astimezone()

                        expected_rain_start_str = expected_rain_start_local.strftime('%H:%M')
                        if expected_rain_start_str.startswith('0'):
                            expected_rain_start_str = expected_rain_start_str[1:]  # Remove leading zero
                        # Calculate the expected rain start time and format it
                        if self.get_total_precipitation_rate() == 0:
                            return "Geen neerslag"
                        else:
                            return f"Neerslag begint om {expected_rain_start_str} en duurt {rain_duration} minuten"
                    else:
                        # The expected rain start time has passed
                        if self.get_total_precipitation_rate() == 0:
                            # No rain expected
                            return "Geen neerslag"
                        else:
                            # More rain expected
                            expected_rain_start_utc = rain_start_time.strftime("%Y-%m-%d %H:%M:%S") + "+0000"
                            expected_rain_start_utc = datetime.strptime(expected_rain_start_utc, "%Y-%m-%d %H:%M:%S%z")
                            expected_rain_start_local = expected_rain_start_utc.replace(tzinfo=timezone.utc).astimezone()

                            expected_rain_start_local_str = expected_rain_start_local.strftime('%H:%M')
                            if expected_rain_start_local_str.startswith('0'):
                                expected_rain_start_local_str = expected_rain_start_local_str[1:]  # Remove leading zero
                            return f"Er wordt regen verwacht om {expected_rain_start_local_str} en duurt {rain_duration}"
            return "Geen neerslag"
        else:
            return "Geen data"

    def new_get_mycastmessage(self) -> Optional[str]:
        """ Method creates message from rain data"""

        rain_data = self.coordinator.data.get('data')

        if rain_data is None:
            return "Geen neerslag"

        rain_start_time, rain_stop_time, rain_duration, rain_stopped = self.get_rain_start_time_and_duration(rain_data)

        # Function to convert a UTC timestamp to local time and format the time without leading zeros
        def format_time(utc_timestamp: datetime) -> str:
            if utc_timestamp is None:
                return "Unknown time"

            #utc_timestamp_str = str(utc_timestamp)
            #time_utc = datetime.fromisoformat(utc_timestamp_str)
            time_local = dt.as_local(utc_timestamp)
            time_str = time_local.strftime('%H:%M')
            return time_str[1:] if time_str.startswith('0') else time_str

        if self.get_current_precipitation() > 0 and rain_start_time:
            # It's currently raining, return an appropriate message
            #if rain_start_time:
                # rain_start_time_utc = datetime.fromisoformat(rain_start_time)
                # rain_start_time_local = dt.as_local(rain_start_time_utc)

                # rain_start_time_utc = rain_start_time.replace(tzinfo=timezone.utc)
                # rain_start_time_local = rain_start_time_utc.astimezone()
            rain_start_time_str = format_time(rain_start_time)

            if rain_stopped:
                return f"1Neerslag begint om {rain_start_time_str} en duurt {rain_duration} minuten en stopt om {format_time(rain_stop_time)}."
            else:
                return f"2Neerslag begint om {rain_start_time_str} en duurt nog {rain_duration} minuten."

        # Handle case where rain_start_time is None
        if rain_start_time is None:
            return "Geen neerslag"

        # It's not currently raining, but rain is expected
        expected_rain_start = rain_start_time - timedelta(minutes=rain_duration)
        #expected_rain_start_utc = datetime.fromisoformat(expected_rain_start)
        #expected_rain_start_local = dt.as_local(expected_rain_start_utc)

        if expected_rain_start > datetime.utcnow():

            # expected_rain_start_utc = expected_rain_start.replace(tzinfo=timezone.utc)
            # expected_rain_start_local = expected_rain_start_utc.astimezone()

            if self.get_total_precipitation_rate() == 0:
                return "Geen neerslag"
            else:
                return f"3Neerslag begint om {format_time(expected_rain_start)} en duurt {rain_duration} minuten"

        else:
            # The expected rain start time has passed
            if self.get_total_precipitation_rate() == 0:
                return "Geen neerslag"
            else:
                #expected_rain_start_utc = datetime.fromisoformat(expected_rain_start)
                #expected_rain_start_local = dt.as_local(expected_rain_start_utc)
                # expected_rain_start_utc = expected_rain_start.replace(tzinfo=timezone.utc)
                # expected_rain_start_local = expected_rain_start_utc.astimezone()
                if rain_stopped:
                    if rain_stop_time:
                        stop_time_str = format_time(rain_stop_time)
                        return f"4Neerslag begint om {rain_start_time_str} en duurt {rain_duration} minuten en stopt om {stop_time_str}."
                    else:
                        return f"5Neerslag begint om {rain_start_time_str} en duurt nog {rain_duration} minuten."
                return f"6Neerslag begint om {format_time(expected_rain_start)} en duurt {rain_duration} minuten."

    def _get_total_precipitation_rate(self) -> float:
        """ Get total precipitation rate rounded to one decimal place """
        # Duration for total precipitation rate is 2 hours - time passed
        data = self.coordinator.data
        total_precipitation_rate = 0

        # Only data in the future
        filtered_data = [
            data_point for data_point in data["data"]
            if datetime.utcfromtimestamp(data_point.get("timestamp")) > datetime.utcnow()
        ]

        if not filtered_data:
            return 0  # No data in the future

        total_precipitation_rates = [
            data_point.get("precipitationrate", 0) for data_point in filtered_data
        ]

        # Calculate the total time period in seconds
        first_data_point = filtered_data[0]
        last_data_point = filtered_data[-1]
        total_time_period = last_data_point["timestamp"] - first_data_point["timestamp"]

        # Convert the total time period to hours
        total_time_period_hours = total_time_period / 3600  # 1 hour = 3600 seconds

        if total_time_period_hours == 0:
            return 0

        # Calculate the total precipitation rate by dividing the sum by the total time period
        total_precipitation_rate = sum(total_precipitation_rates) / total_time_period_hours

        # Round the result to one decimal place
        total_precipitation_rate = round(total_precipitation_rate, 1)

        return total_precipitation_rate

    def _get_total_precipitation_rate_for_next_hour(self) -> float:
        """ Calcutate the total precipitation rate in mm/h for the upcoming hour """
        data = self.coordinator.data
        current_time = datetime.utcnow()
        total_precipitation_rate = 0

        # Calculate the time for next hour from the current time
        next_hour = current_time + timedelta(hours=1)

        for data_point in data["data"]:
            # Each data point is 5 minutes, and the precipitation rate value is in mm/hour
            entry_timestamp = datetime.utcfromtimestamp(data_point.get("timestamp"))

            # Count total precipitation rate only when time > now
            if entry_timestamp > datetime.utcnow():

                # Check if the entry falls within the next hour
                if current_time <= entry_timestamp <= next_hour:
                    total_precipitation_rate += data_point.get("precipitationrate", 0)

        return round(total_precipitation_rate, 1)

    def filter_data_by_time(self, data: list[dict[str, any]], start_time: datetime, end_time: datetime) -> list[dict[str, any]]:
        return [
            data_point for data_point in data
            if start_time <= datetime.utcfromtimestamp(data_point.get("timestamp")) <= end_time
        ]

    def calculate_total_precipitation_rate(
        self, data: dict[str, any], start_time: datetime, end_time: datetime
    ) -> float:
        filtered_data = self.filter_data_by_time(data["data"], start_time, end_time)

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
        data: dict[str, Any] = self.coordinator.data
        current_time: datetime = datetime.utcnow()
        end_time: datetime = current_time + timedelta(hours=2)
        return self.calculate_total_precipitation_rate(data, current_time, end_time)

    def get_total_precipitation_rate_for_next_hour(self) -> float:
        """ Calculate the total precipitation rate in mm/h for the upcoming hour """
        data: dict[str, Any] = self.coordinator.data
        current_time: datetime = datetime.utcnow()
        end_time: datetime = current_time + timedelta(hours=1)
        return self.calculate_total_precipitation_rate(data, current_time, end_time)

    def old_get_current_precipitation(self) -> float:
        data = self.coordinator.data
        current_time = datetime.utcnow()
        current_precipitation_rate = 0

        for data_point in data["data"]:
            if datetime.utcfromtimestamp(data_point.get("timestamp")) > datetime.utcnow():
                data_point_timestamp = datetime.fromtimestamp(data_point.get("timestamp"))
                five_minutes_later = data_point_timestamp + timedelta(minutes=5)
                if data_point_timestamp < current_time < five_minutes_later:
                    current_precipitation_rate = data_point.get("precipitationrate", 0)
        return current_precipitation_rate

    def get_current_precipitation(self) -> float:
        """Get the current precipitation rate."""
        data: dict[str, Any] = self.coordinator.data
        current_time: datetime = datetime.utcnow()
        current_precipitation_rate: float = 0
        current_precipitation_type: str = '-'

        for data_point in data["data"]:
            data_point_timestamp = datetime.utcfromtimestamp(data_point.get("timestamp"))

            # Check if the data point is within the last 5 minutes
            if data_point_timestamp < current_time < data_point_timestamp + timedelta(minutes=5):
                current_precipitation_rate = data_point.get("precipitationrate", 0)
                current_precipitation_type = data_point.get("precipitationtype", "-")

        return current_precipitation_rate  # , current_precipitation_type

    def get_current_precipitation_rate_desc(self) -> str:
        """Get the description of the current precipitation rate."""
        data: dict[str, Any] = self.coordinator.data
        current_time: datetime = datetime.utcnow()
        current_precipitation_rate_desc: str = NO_PRECIPITATION

        precipitation_categories = [
            (10, "Zware regen"),
            (2.5, "Matige regen"),
            (1, "Lichte regen"),
            (0, "Motregen"),
        ]

        for entry in data["data"]:
            entry_timestamp = datetime.utcfromtimestamp(entry.get("timestamp"))
            five_minutes_later = entry_timestamp + timedelta(minutes=5)

            if entry_timestamp < current_time < five_minutes_later:
                current_precipitation_rate = entry.get("precipitationrate", 0)

                for threshold, category in precipitation_categories:
                    if current_precipitation_rate > threshold:
                        current_precipitation_rate_desc = category
                        break

        return current_precipitation_rate_desc

    def get_current_precipitation_type(self) -> str:
        """Get the type of current precipitation (rain, snow, etc.)."""
        precipitation_data = self.coordinator.data["data"]
        current_time = datetime.utcnow()
        current_type = NO_PRECIPITATION

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
                    if rain_start_time_utc is None:
                        rain_start_time_utc = data_point_timestamp
                    rain_stopped = False
                    if rain_restart_time_utc is None:
                        rain_duration += 5
                        rain_stopped = False
                    if rain_restart_time_utc is None and rain_stop_time_utc is not None:
                        rain_restart_time_utc = data_point_timestamp
                # Check if there's a gap in precipitation
                elif rain_start_time_utc is not None and rain_stop_time_utc is None:
                    rain_stop_time_utc = data_point_timestamp
                    #rain_stopped = True

        return rain_start_time_utc, rain_stop_time_utc, rain_restart_time_utc, rain_duration, rain_stopped


testdata: dict[str, list[dict]] = {"data":[{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697945700,"time":"2023-10-22T03:35:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697946000,"time":"2023-10-22T03:40:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697946300,"time":"2023-10-22T03:45:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697946600,"time":"2023-10-22T03:50:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697946900,"time":"2023-10-22T03:55:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697947200,"time":"2023-10-22T04:00:00Z"},{"precipitationrate":0.1,"precipitationtype":"rain","timestamp":1697947500,"time":"2023-10-22T04:05:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697947800,"time":"2023-10-22T04:10:00Z"},{"precipitationrate":0.1,"precipitationtype":"rain","timestamp":1697948100,"time":"2023-10-22T04:15:00Z"},{"precipitationrate":0.2,"precipitationtype":"rain","timestamp":1697948400,"time":"2023-10-22T04:20:00Z"},{"precipitationrate":0.1,"precipitationtype":"rain","timestamp":1697948700,"time":"2023-10-22T04:25:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697949000,"time":"2023-10-22T04:30:00Z"},{"precipitationrate":0.1,"precipitationtype":"rain","timestamp":1697949300,"time":"2023-10-22T04:35:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697949600,"time":"2023-10-22T04:40:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697949900,"time":"2023-10-22T04:45:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697950200,"time":"2023-10-22T04:50:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697950500,"time":"2023-10-22T04:55:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697950800,"time":"2023-10-22T05:00:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697951100,"time":"2023-10-22T05:05:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697951400,"time":"2023-10-22T05:10:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697951700,"time":"2023-10-22T05:15:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697952000,"time":"2023-10-22T05:20:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697952300,"time":"2023-10-22T05:25:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697952600,"time":"2023-10-22T05:30:00Z"},{"precipitationrate":0,"precipitationtype":"rain","timestamp":1697952900,"time":"2023-10-22T05:35:00Z"}],"nowcastmessage":{"en":"Showers starting at {1697947500}, lasting 5 minutes","de":"Niederschlag beginnt um {1697947500} und dauert 5 Minuten","nl":"Neerslag begint om {1697947500} en duurt 5 minuten"}}