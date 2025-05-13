# config_flow.py

import logging

import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER: logging.Logger = logging.getLogger(__name__)

CONF_PLACE = "place"
DEFAULT_LATITUDE: float = "52.7875"
DEFAULT_LONGITUDE: float = "4.79861"
DEFAULT_DATA_REFRESH_INTERVAL: int = 300
DEFAULT_NOTIFICATION_LIMIT: int = 0  # show notification on all values
HINT = "https://www.coordinatenbepalen.nl"


@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow):
    """Config flow for Buienalarm."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(
        self,
        user_input: dict[str, any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step when the user initiates a config flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # place = user_input[CONF_PLACE]
            latitude = user_input[CONF_LATITUDE]
            longitude = user_input[CONF_LONGITUDE]
            # notification_limit = user_input["notification_limit"]
            # refresh_interval = user_input["refresh_interval"]
            # Validate user input (e.g., check if latitude and longitude are valid)
            try:
                # Validate coordinates
                if not is_valid_coordinates(latitude, longitude):
                    raise InvalidCoordinatesError
                await validate_coordinates(latitude, longitude)
            except InvalidCoordinatesError:
                errors["base"] = "invalid_coordinates"
            else:
                # Store the configuration data in the entry
                return self.async_create_entry(
                    title="Buienalarm",
                    data=user_input,
                    # data={
                    #    CONF_PLACE: place,
                    #    CONF_LATITUDE: latitude,
                    #    CONF_LONGITUDE: longitude,
                    #    "notification_limit": notification_limit,
                    #    "refresh_interval": refresh_interval,
                    # },
                )

        # Create a description for the refresh_interval field
        help_text = (
            "The refresh interval in seconds determines how often the data is "
            "retrieved from the Buienalarm API. A lower value will result in more frequent "
            "updates but may consume more resources. The default value is 300 seconds "
            "(5 minutes)."
        )

        # Define the schema for the configuration options
        data_schema = vol.Schema(
            {
                vol.Required(CONF_PLACE): str,
                vol.Required(CONF_LATITUDE, default=DEFAULT_LATITUDE): float,
                vol.Required(CONF_LONGITUDE, default=DEFAULT_LONGITUDE): float,
                vol.Optional(
                    "notification_limit",
                    default=DEFAULT_NOTIFICATION_LIMIT,  # Default to 0 mm/h (notify on every value))
                    description="Enter the notification limit in mm/h",
                ): int,
                vol.Optional(
                    "refresh_interval",
                    default=DEFAULT_DATA_REFRESH_INTERVAL,  # Default to 300 seconds (5 minutes)
                    description="Enter the refresh interval in seconds",
                ): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> "BuienalarmOptionsFlowHandler":
        return BuienalarmOptionsFlowHandler(config_entry)


async def validate_coordinates(latitude, longitude):
    # Implement your validation logic for latitude and longitude here
    errors = {}
    if not is_valid_latitude(latitude) or not is_valid_longitude(longitude):
        errors["base"] = "invalid_coordinates"
        raise InvalidCoordinatesError("Invalid coordinates")


def is_valid_latitude(latitude):
    # Implement validation logic for latitude
    try:
        # Convert the latitude to a float
        latitude_float = float(latitude)

        # Check if the latitude is within the valid range (-90 to 90 degrees)
        if -90.0 <= latitude_float <= 90.0:
            return True
        else:
            return False
    except ValueError:
        # If the conversion to float fails, it's not a valid latitude
        return False


def is_valid_longitude(longitude):
    # Implement validation logic for longitude
    try:
        # Convert the longitude to a float
        longitude_float = float(longitude)

        # Check if the longitude is within the valid range (-180 to 180 degrees)
        if -180.0 <= longitude_float <= 180.0:
            return True
        else:
            return False
    except ValueError:
        # If the conversion to float fails, it's not a valid longitude
        return False


class BuienalarmOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a Buienalarm options flow."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        self._entry_id = entry.entry_id
        self._entry = entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Initialize the options flow."""
        if user_input is not None:
            # Handle user input and update options here
            # For example, you can update options like this:
            # self.config_entry.options[CONF_NAME] = user_input[CONF_NAME]
            # return self.async_create_entry(title="", data={})
            return self.async_create_entry(title="", data=user_input)

        # Present options to the user
        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(),
        )

    def _get_options_schema(self):
        """Return the schema for the options form."""
        return vol.Schema({
            vol.Required(CONF_NAME, default="Buienalarm", description="Configuration name"): str,
            vol.Required(CONF_PLACE, default=self.hass.config.location_name, description="Configuration place"): str,
            vol.Required(CONF_LATITUDE, default=DEFAULT_LATITUDE): float,
            vol.Required(CONF_LONGITUDE, default=DEFAULT_LONGITUDE): float,
            vol.Optional(
                "notification_limit",
                default=DEFAULT_NOTIFICATION_LIMIT,  # Default to 0 mm/h (notify on every value))
                description="Enter the notification limit in mm/h",
            ): int,
            vol.Optional(
                "refresh_interval",
                default=DEFAULT_DATA_REFRESH_INTERVAL,  # Default to 300 seconds (5 minutes)
                description="Enter the refresh interval in seconds",
            ): int,
        })


def is_valid_coordinates(latitude, longitude):
    try:
        latitude = float(latitude)
        longitude = float(longitude)
        return -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0
    except (ValueError, TypeError):
        return False


class InvalidCoordinatesError(exceptions.HomeAssistantError):
    """Exception to indicate invalid coordinates."""
    pass
