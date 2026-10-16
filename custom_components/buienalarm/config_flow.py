"""Config flow for the Buienalarm integration.

This module implements the user-facing configuration flow and the accompanying
options flow. It validates latitude/longitude coordinates, ensures each
configuration entry has a stable ``unique_id`` (lat_lon combo), and exposes
user-editable options such as *refresh_interval* and *notification_limit*.

The flow follows Home Assistant best-practices:
    • Uses VERSION tracking for forward migrations.
    • Aborts if an identical ``unique_id`` is already configured.
    • Adds exhaustive type-hints and detailed docstrings.
    • Employs lazy ``%`` interpolation for all logging calls
      (pylint-warning W1203).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Final

import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import DOMAIN, NAME

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Defaults & helpers
# -----------------------------------------------------------------------------
DEFAULT_LATITUDE: Final[float] = 52.7875
DEFAULT_LONGITUDE: Final[float] = 4.79861
DEFAULT_REFRESH_INTERVAL: Final[int] = 300  # seconds (5 min)
DEFAULT_NOTIFICATION_LIMIT: Final[int] = 0  # mm/h – notify on any value


def _is_valid_coordinates(latitude: float | str, longitude: float | str) -> bool:
    """Return *True* if *latitude* and *longitude* are within valid ranges."""
    try:
        lat: float = float(str(latitude).replace(",", "."))
        lon: float = float(str(longitude).replace(",", "."))
    except (TypeError, ValueError):
        return False

    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def _get_default_coordinates(hass: Any) -> tuple[float, float]:
    """Get default latitude and longitude from hass.config or fallback."""
    if hass is not None:
        config = getattr(hass, "config", None)
        if config is not None:
            lat = getattr(config, "latitude", None)
            lon = getattr(config, "longitude", None)
            if lat is not None and lon is not None:
                return float(lat), float(lon)
    return DEFAULT_LATITUDE, DEFAULT_LONGITUDE


def _parse_refresh_interval(val: Any) -> int:
    """Parse refresh interval value returning -1 if invalid or boolean."""
    if isinstance(val, bool):
        return -1
    try:
        return int(val)
    except (ValueError, TypeError, OverflowError):
        return -1


def _parse_notification_limit(val: Any) -> float:
    """Parse notification limit value returning -1.0 if invalid, non-finite, or boolean."""
    if isinstance(val, bool):
        return -1.0
    try:
        limit = float(val)
        return -1.0 if math.isnan(limit) or math.isinf(limit) else limit
    except (ValueError, TypeError, OverflowError):
        return -1.0


def _validate_flow_input(
    user_input: dict[str, Any],
) -> tuple[dict[str, str], float, float, int, float]:
    """Validate user input for config and options flows."""
    errors: dict[str, str] = {}
    latitude_raw: str = str(user_input[CONF_LATITUDE]).replace(",", ".")
    longitude_raw: str = str(user_input[CONF_LONGITUDE]).replace(",", ".")

    refresh_interval = _parse_refresh_interval(
        user_input.get("refresh_interval", DEFAULT_REFRESH_INTERVAL)
    )
    notification_limit = _parse_notification_limit(
        user_input.get("notification_limit", DEFAULT_NOTIFICATION_LIMIT)
    )

    if not _is_valid_coordinates(latitude_raw, longitude_raw):
        errors["base"] = "invalid_coordinates"
    elif refresh_interval < 60:
        errors["base"] = "invalid_refresh_interval"
    elif notification_limit < 0:
        errors["base"] = "invalid_notification_limit"

    lat = float(latitude_raw) if not errors else 0.0
    lon = float(longitude_raw) if not errors else 0.0

    return errors, lat, lon, refresh_interval, notification_limit


def _build_flow_schema(
    defaults: dict[str, Any], is_optional: bool = False
) -> vol.Schema:
    """Build the voluptuous schema with selectors for forms."""
    opt_or_req = vol.Optional if is_optional else vol.Required
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, NAME)): TextSelector(),
            vol.Required(
                CONF_LATITUDE, default=defaults.get(CONF_LATITUDE, DEFAULT_LATITUDE)
            ): NumberSelector(
                NumberSelectorConfig(
                    step="any",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_LONGITUDE, default=defaults.get(CONF_LONGITUDE, DEFAULT_LONGITUDE)
            ): NumberSelector(
                NumberSelectorConfig(
                    step="any",
                    mode=NumberSelectorMode.BOX,
                )
            ),
            opt_or_req(
                "notification_limit",
                default=defaults.get(
                    "notification_limit", DEFAULT_NOTIFICATION_LIMIT
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    step=0.1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="mm/h",
                )
            ),
            opt_or_req(
                "refresh_interval",
                default=defaults.get("refresh_interval", DEFAULT_REFRESH_INTERVAL),
            ): NumberSelector(
                NumberSelectorConfig(
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
        }
    )


# -----------------------------------------------------------------------------
# Config Flow
# -----------------------------------------------------------------------------


class BuienalarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Buienalarm config flow."""

    VERSION: Final[int] = 2
    CONNECTION_CLASS: Final[str] = config_entries.CONN_CLASS_CLOUD_POLL

    # ---------------------------------------------------------------------
    # Initial step
    # ---------------------------------------------------------------------
    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the first step when the user starts the flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, lat, lon, refresh_interval, notification_limit = _validate_flow_input(user_input)

            if not errors:
                unique_id: str = f"{lat}_{lon}"

                # Register unique_id with HA and abort if it already exists.
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                _LOGGER.debug("Creating new config entry")
                location_name = user_input.get(
                    CONF_NAME, NAME
                )  # Default name if not provided

                lat_title = round(lat, 4)
                lon_title = round(lon, 4)

                return self.async_create_entry(
                    title=f"{location_name} ({lat_title}, {lon_title})",
                    data={
                        CONF_NAME: location_name,
                        CONF_LATITUDE: lat,
                        CONF_LONGITUDE: lon,
                        "location_id": unique_id,
                        "location_name": location_name,
                        "notification_limit": notification_limit,
                        "refresh_interval": refresh_interval,
                    },
                )

        return self._show_form(errors)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _show_form(self, errors: dict[str, str] | None = None) -> FlowResult:
        """Return the form definition for the *user* step."""
        default_lat, default_lon = _get_default_coordinates(self.hass)
        defaults = {
            CONF_NAME: NAME,
            CONF_LATITUDE: default_lat,
            CONF_LONGITUDE: default_lon,
            "notification_limit": DEFAULT_NOTIFICATION_LIMIT,
            "refresh_interval": DEFAULT_REFRESH_INTERVAL,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=_build_flow_schema(defaults, is_optional=True),
            errors=errors or {},
        )

    # ------------------------------------------------------------------
    # Options flow
    # ------------------------------------------------------------------
    @staticmethod
    @callback  # noqa: D401 – Home Assistant pattern
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BuienalarmOptionsFlow:
        """Return the options flow handler."""
        return BuienalarmOptionsFlow(config_entry)


# -----------------------------------------------------------------------------
# Options Flow
# -----------------------------------------------------------------------------


class BuienalarmOptionsFlow(config_entries.OptionsFlow):
    """Handle the Buienalarm options flow."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:  # noqa: D401
        self._entry: Final[config_entries.ConfigEntry] = entry

    # --------------------------------------------------------------
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the Buienalarm options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, lat, lon, refresh_interval, notification_limit = _validate_flow_input(user_input)

            if not errors:
                _LOGGER.debug(
                    "Updating options for entry %s", self._entry.entry_id
                )
                user_input[CONF_LATITUDE] = lat
                user_input[CONF_LONGITUDE] = lon
                user_input["refresh_interval"] = refresh_interval
                user_input["notification_limit"] = notification_limit
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self._options_schema(user_input),
            errors=errors,
        )

    # --------------------------------------------------------------
    def _options_schema(
        self, user_input: dict[str, Any] | None = None
    ) -> vol.Schema:  # noqa: D401
        """Return schema for the options form."""
        options = user_input if user_input is not None else self._entry.options
        data = self._entry.data
        defaults = {
            CONF_NAME: options.get(CONF_NAME, data.get(CONF_NAME, NAME)),
            CONF_LATITUDE: options.get(
                CONF_LATITUDE, data.get(CONF_LATITUDE, DEFAULT_LATITUDE)
            ),
            CONF_LONGITUDE: options.get(
                CONF_LONGITUDE, data.get(CONF_LONGITUDE, DEFAULT_LONGITUDE)
            ),
            "notification_limit": options.get(
                "notification_limit",
                data.get("notification_limit", DEFAULT_NOTIFICATION_LIMIT),
            ),
            "refresh_interval": options.get(
                "refresh_interval",
                data.get("refresh_interval", DEFAULT_REFRESH_INTERVAL),
            ),
        }
        return _build_flow_schema(defaults, is_optional=False)


# -----------------------------------------------------------------------------
# Custom Exceptions
# -----------------------------------------------------------------------------


class InvalidCoordinatesError(exceptions.HomeAssistantError):
    """Raised when the supplied coordinates are outside valid ranges."""

    def __init__(self, latitude: Any, longitude: Any) -> None:  # noqa: D401
        super().__init__(
            f"Invalid coordinates provided: lat={latitude!r}, lon={longitude!r}"
        )
