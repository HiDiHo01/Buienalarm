"""Config flow for the Buienalarm integration.

This module implements the user‑facing configuration flow and the accompanying
options flow.  It validates latitude/longitude coordinates, ensures each
configuration entry has a stable ``unique_id`` (lat_lon combo), and exposes
user‑editable options such as *refresh_interval* and *notification_limit*.

The flow follows Home Assistant best‑practices:
    • Uses VERSION tracking for forward migrations.
    • Aborts if an identical ``unique_id`` is already configured.
    • Adds exhaustive type‑hints and detailed docstrings.
    • Employs lazy ``%`` interpolation for all logging calls
      (pylint‑warning W1203).
"""
from __future__ import annotations

import logging
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

from .const import DOMAIN, NAME

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Defaults & helpers
# -----------------------------------------------------------------------------
DEFAULT_LATITUDE: Final[float] = 52.7875
DEFAULT_LONGITUDE: Final[float] = 4.79861
DEFAULT_REFRESH_INTERVAL: Final[int] = 300  # seconds (5 min)
DEFAULT_NOTIFICATION_LIMIT: Final[int] = 0   # mm/h – notify on any value


def _is_valid_coordinates(latitude: float | str, longitude: float | str) -> bool:
    """Return *True* if *latitude* and *longitude* are within valid ranges."""
    try:
        lat: float = float(str(latitude).replace(",", "."))
        lon: float = float(str(longitude).replace(",", "."))
    except (TypeError, ValueError):
        return False

    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


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
            latitude_raw: str = str(user_input[CONF_LATITUDE]).replace(",", ".")
            longitude_raw: str = str(user_input[CONF_LONGITUDE]).replace(",", ".")

            if not _is_valid_coordinates(latitude_raw, longitude_raw):
                errors["base"] = "invalid_coordinates"
            else:
                unique_id: str = f"{latitude_raw}_{longitude_raw}"

                # Register unique_id with HA and abort if it already exists.
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                _LOGGER.debug("Creating new config entry: %s", unique_id)
                location_name = user_input.get(CONF_NAME, NAME)  # Default name if not provided

                return self.async_create_entry(
                    title=f"{location_name} ({latitude_raw}, {longitude_raw})",
                    data={
                        CONF_NAME: user_input.get(CONF_NAME, NAME),
                        CONF_LATITUDE: float(latitude_raw),
                        CONF_LONGITUDE: float(longitude_raw),
                        "location_id": unique_id,
                        "location_name": location_name,
                        "notification_limit": user_input.get(
                            "notification_limit", DEFAULT_NOTIFICATION_LIMIT
                        ),
                        "refresh_interval": user_input.get(
                            "refresh_interval", DEFAULT_REFRESH_INTERVAL
                        ),
                    },
                )

        return self._show_form(errors)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _show_form(self, errors: dict[str, str] | None = None) -> FlowResult:
        """Return the form definition for the *user* step."""
        data_schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=NAME): str,
                vol.Required(CONF_LATITUDE, default=DEFAULT_LATITUDE): float,
                vol.Required(CONF_LONGITUDE, default=DEFAULT_LONGITUDE): float,
                vol.Optional(
                    "notification_limit", default=DEFAULT_NOTIFICATION_LIMIT
                ): int,
                vol.Optional(
                    "refresh_interval", default=DEFAULT_REFRESH_INTERVAL
                ): int,
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
    @callback  # noqa: D401 – Home Assistant pattern
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "BuienalarmOptionsFlow":
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
        if user_input is not None:
            _LOGGER.debug(
                "Updating options for entry %s: %s", self._entry.entry_id, user_input
            )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self._options_schema(),
        )

    # --------------------------------------------------------------
    def _options_schema(self) -> vol.Schema:  # noqa: D401
        """Return schema for the options form."""
        existing = self._entry.options
        return vol.Schema(
            {
                vol.Required(
                    CONF_NAME,
                    default=existing.get(CONF_NAME, NAME),
                ): str,
                vol.Required(
                    CONF_LATITUDE,
                    default=existing.get(CONF_LATITUDE, DEFAULT_LATITUDE),
                ): float,
                vol.Required(
                    CONF_LONGITUDE,
                    default=existing.get(CONF_LONGITUDE, DEFAULT_LONGITUDE),
                ): float,
                vol.Required(
                    "notification_limit",
                    default=existing.get(
                        "notification_limit", DEFAULT_NOTIFICATION_LIMIT
                    ),
                ): int,
                vol.Required(
                    "refresh_interval",
                    default=existing.get("refresh_interval", DEFAULT_REFRESH_INTERVAL),
                ): int,
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
