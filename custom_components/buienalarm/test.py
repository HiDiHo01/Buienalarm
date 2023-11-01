from datetime import datetime, timezone
from homeassistant.util import dt
from homeassistant.core import HomeAssistant

# Function to convert a UTC timestamp to local time and format the time without leading zeros
def format_time(utc_timestamp: datetime):
    if utc_timestamp is None:
        return "Unknown time"

    time_local = dt.as_local(utc_timestamp)
    return time_local
    time_str = time_local.strftime('%H:%M')
    return time_str.lstrip('0')

# Get the Home Assistant timezone
ha_instance = HomeAssistant()
ha_timezone = dt.get_time_zone(ha_instance)
print(ha_timezone)



# Example usage:
utc_timestamp = "2023-10-23T03:05:00Z"
print(utc_timestamp)
#print(format_time(utc_timestamp))
utc_timestamp = datetime.fromisoformat(utc_timestamp)
print(format_time(utc_timestamp))
utc_timestamp = utc_timestamp.strftime("%Y-%m-%d %H:%M:%S") + "+0000"
#print(format_time(utc_timestamp))
utc_timestamp = datetime.strptime(utc_timestamp, "%Y-%m-%d %H:%M:%S%z")
print(format_time(utc_timestamp))
utc_timestamp = utc_timestamp.replace(tzinfo=timezone.utc).astimezone()
print(format_time(utc_timestamp))
utc_timestamp = dt.as_local(dt.utc_from_timestamp(int(utc_timestamp.timestamp())))
print(format_time(utc_timestamp))
