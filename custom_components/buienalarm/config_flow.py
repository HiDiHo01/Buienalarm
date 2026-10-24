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

from decimal import Decimal, InvalidOperation
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
from homeassistant.helpers import selector

from .const import DOMAIN, NAME

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Defaults & helpers
# -----------------------------------------------------------------------------
DEFAULT_LATITUDE: Final[float] = 52.7875
DEFAULT_LONGITUDE: Final[float] = 4.79861
DEFAULT_REFRESH_INTERVAL: Final[int] = 300  # seconds (5 min)
DEFAULT_NOTIFICATION_LIMIT: Final[int] = 0  # mm/h – notify on any value

_LATITUDE_SELECTOR: Final[selector.NumberSelector] = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=-90.0,
        max=90.0,
        step="any",
        mode=selector.NumberSelectorMode.BOX,
    )
)

_LONGITUDE_SELECTOR: Final[selector.NumberSelector] = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=-180.0,
        max=180.0,
        step="any",
        mode=selector.NumberSelectorMode.BOX,
    )
)

_NOTIFICATION_LIMIT_SCHEMA: Final[selector.NumberSelector] = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0.0,
        step=1.0,
        mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement="mm/h",
    )
)

_REFRESH_INTERVAL_SCHEMA: Final[selector.NumberSelector] = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=60.0,
        step=1.0,
        mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement="s",
    )
)


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


def _parse_int_option(value: Any, min_value: int) -> int | None:
    """Safely parse a non-boolean integer option >= min_value, returning None if invalid."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= min_value else None
    if isinstance(value, str):
        try:
            dec = Decimal(value)
        except (InvalidOperation, TypeError, ValueError):
            return None
        if not dec.is_finite() or dec < min_value or dec % 1 != 0:
            return None
        return int(dec)
    try:
        val_float = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if (
        not math.isfinite(val_float)
        or val_float < min_value
        or not val_float.is_integer()
    ):
        return None

    return int(val_float)


def _validate_flow_input(
    user_input: dict[str, Any],
) -> tuple[dict[str, str], float, float, int, int]:
    """Validate flow input and return errors and normalized values."""
    errors: dict[str, str] = {}
    latitude_raw: str = str(user_input.get(CONF_LATITUDE, "")).replace(",", ".")
    longitude_raw: str = str(user_input.get(CONF_LONGITUDE, "")).replace(",", ".")
    notif_limit = user_input.get("notification_limit")
    refresh_int = user_input.get("refresh_interval")

    parsed_notif = DEFAULT_NOTIFICATION_LIMIT
    parsed_refresh = DEFAULT_REFRESH_INTERVAL

    if not _is_valid_coordinates(latitude_raw, longitude_raw):
        errors["base"] = "invalid_coordinates"

    if notif_limit is not None:
        parsed = _parse_int_option(notif_limit, 0)
        if parsed is None:
            errors.setdefault("base", "invalid_notification_limit")
        else:
            parsed_notif = parsed

    if refresh_int is not None:
        parsed = _parse_int_option(refresh_int, 60)
        if parsed is None:
            errors.setdefault("base", "invalid_refresh_interval")
        else:
            parsed_refresh = parsed

    try:
        lat_float = float(latitude_raw) if not errors else 0.0
        lon_float = float(longitude_raw) if not errors else 0.0
    except (TypeError, ValueError):
        errors["base"] = "invalid_coordinates"
        lat_float = 0.0
        lon_float = 0.0

    return errors, lat_float, lon_float, parsed_notif, parsed_refresh


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
            errors, lat_float, lon_float, notif_limit, refresh_int = (
                _validate_flow_input(user_input)
            )
            if not errors:
                unique_id: str = f"{lat_float}_{lon_float}"

                # Register unique_id with HA and abort if it already exists.
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                _LOGGER.debug("Creating new config entry")
                location_name = user_input.get(CONF_NAME, NAME)

                lat_title = round(lat_float, 4)
                lon_title = round(lon_float, 4)

                return self.async_create_entry(
                    title=f"{location_name} ({lat_title}, {lon_title})",
                    data={
                        CONF_NAME: location_name,
                        CONF_LATITUDE: lat_float,
                        CONF_LONGITUDE: lon_float,
                        "location_id": unique_id,
                        "location_name": location_name,
                        "notification_limit": notif_limit,
                        "refresh_interval": refresh_int,
                    },
                )

        return self._show_form(errors)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _show_form(self, errors: dict[str, str] | None = None) -> FlowResult:
        """Return the form definition for the *user* step."""
        default_lat, default_lon = _get_default_coordinates(self.hass)

        data_schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=NAME): selector.TextSelector(),
                vol.Required(CONF_LATITUDE, default=default_lat): _LATITUDE_SELECTOR,
                vol.Required(CONF_LONGITUDE, default=default_lon): _LONGITUDE_SELECTOR,
                vol.Optional(
                    "notification_limit", default=DEFAULT_NOTIFICATION_LIMIT
                ): _NOTIFICATION_LIMIT_SCHEMA,
                vol.Optional(
                    "refresh_interval", default=DEFAULT_REFRESH_INTERVAL
                ): _REFRESH_INTERVAL_SCHEMA,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
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
            errors, lat_float, lon_float, notif_limit, refresh_int = (
                _validate_flow_input(user_input)
            )
            if not errors:
                _LOGGER.debug("Updating options for entry %s", self._entry.entry_id)
                user_input[CONF_LATITUDE] = lat_float
                user_input[CONF_LONGITUDE] = lon_float
                user_input["notification_limit"] = notif_limit
                user_input["refresh_interval"] = refresh_int
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
        return vol.Schema(
            {
                vol.Required(
                    CONF_NAME,
                    default=options.get(CONF_NAME, data.get(CONF_NAME, NAME)),
                ): selector.TextSelector(),
                vol.Required(
                    CONF_LATITUDE,
                    default=options.get(
                        CONF_LATITUDE, data.get(CONF_LATITUDE, DEFAULT_LATITUDE)
                    ),
                ): _LATITUDE_SELECTOR,
                vol.Required(
                    CONF_LONGITUDE,
                    default=options.get(
                        CONF_LONGITUDE, data.get(CONF_LONGITUDE, DEFAULT_LONGITUDE)
                    ),
                ): _LONGITUDE_SELECTOR,
                vol.Required(
                    "notification_limit",
                    default=options.get(
                        "notification_limit",
                        data.get("notification_limit", DEFAULT_NOTIFICATION_LIMIT),
                    ),
                ): _NOTIFICATION_LIMIT_SCHEMA,
                vol.Required(
                    "refresh_interval",
                    default=options.get(
                        "refresh_interval",
                        data.get("refresh_interval", DEFAULT_REFRESH_INTERVAL),
                    ),
                ): _REFRESH_INTERVAL_SCHEMA,
            }
        )


# -----------------------------------------------------------------------------
# Custom Exceptions
# -----------------------------------------------------------------------------


class InvalidCoordinatesError(exceptions.HomeAssistantError):
    """Raised when the supplied coordinates are outside valid ranges."""

    def __init__(self, latitude: Any, longitude: Any) -> None:  # noqa: D401
        super().__init__(
            f"Invalid coordinates provided: lat={latitude!r}, lon={longitude!r}"
        )
