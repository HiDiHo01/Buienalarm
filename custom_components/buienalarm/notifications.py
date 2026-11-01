"""Persistent precipitation notifications from the shared forecast coordinator."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from homeassistant.components import persistent_notification
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import BuienalarmConfigEntry, BuienalarmDataUpdateCoordinator
from .entity import _as_float, _safe_get

_KIND_KEYS = {
    "rain": "rain",
    "freezing rain": "freezing_rain",
    "snow": "snow",
    "wet snow": "wet_snow",
    "mix": "mix",
    "mix of rain and snow": "mix",
}
_TRANSLATION_PREFIX = f"component.{DOMAIN}.common."


@dataclass(frozen=True)
class _Forecast:
    """A validated, unexpired five-minute precipitation forecast bin."""

    start: datetime
    end: datetime
    rate: float
    kind: str


def _next_precipitation(data: object, limit: float, now: datetime) -> _Forecast | None:
    """Find the earliest unexpired bin strictly above the configured intensity."""
    if not isinstance(data, Mapping):
        return None
    payload = data.get("timeseries", data)
    if not isinstance(payload, Mapping):
        return None
    points = payload.get("data")
    if not isinstance(points, list):
        return None

    result: _Forecast | None = None
    now_ts = now.timestamp()
    for point in points:
        timestamp = _as_float(_safe_get(point, "timestamp"))
        rate = _as_float(_safe_get(point, "precipitationrate"))
        if (
            timestamp is None
            or rate is None
            or timestamp + 300 <= now_ts
            or rate <= limit
        ):
            continue
        try:
            start = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            end = datetime.fromtimestamp(timestamp + 300, tz=timezone.utc)
        except ValueError, OverflowError, OSError:
            continue
        raw_kind = _safe_get(point, "precipitationtype")
        kind = (
            _KIND_KEYS.get(raw_kind.strip().lower(), "unknown")
            if isinstance(raw_kind, str)
            else "unknown"
        )
        if result is None or start < result.start:
            result = _Forecast(start, end, rate, kind)
    return result


class PrecipitationNotifications:
    """Keep one translated precipitation notification per configured location."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: BuienalarmConfigEntry,
        coordinator: BuienalarmDataUpdateCoordinator,
        translations: dict[str, str],
    ) -> None:
        """Subscribe to validated coordinator updates; cleanup belongs to the entry."""
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._translations = translations
        self._notification_id = f"{DOMAIN}_precipitation_{entry.entry_id}"
        self._last_notification: tuple[str, str] | None = None
        self._cancel_expiry: Callable[[], None] | None = None
        self._unsubscribe = coordinator.async_add_listener(self.async_update)

    @callback
    def async_update(self) -> None:
        """Update or dismiss the notification without making additional API requests."""
        if self._cancel_expiry is not None:
            self._cancel_expiry()
            self._cancel_expiry = None

        # Config-flow defaults apply to older entries as well; options take precedence.
        limit = _as_float(
            self._entry.options.get(
                "notification_limit", self._entry.data.get("notification_limit", 0)
            )
        )
        forecast = None
        if self._coordinator.last_update_success and limit is not None and limit >= 0:
            forecast = _next_precipitation(
                self._coordinator.data, limit, datetime.now(timezone.utc)
            )
        if forecast is None:
            self._dismiss()
            return

        location = self._entry.options.get(
            CONF_NAME,
            self._entry.data.get("location_name")
            or self._entry.data.get(CONF_NAME)
            or self._entry.title,
        )
        title = self._translations[
            f"{_TRANSLATION_PREFIX}precipitation_notification_title"
        ].format(location=location)
        message = self._translations[
            f"{_TRANSLATION_PREFIX}precipitation_notification_message"
        ].format(
            precipitation_type=self._translations[
                f"{_TRANSLATION_PREFIX}precipitation_type_{forecast.kind}"
            ],
            rate=f"{forecast.rate:g}",
            start=dt_util.as_local(forecast.start).strftime("%Y-%m-%d %H:%M %Z"),
        )
        if self._last_notification != (title, message):
            persistent_notification.async_create(
                self._hass, message, title=title, notification_id=self._notification_id
            )
            self._last_notification = (title, message)

        # A long refresh interval must not leave an expired forecast on screen.
        self._cancel_expiry = async_track_point_in_utc_time(
            self._hass, self._async_expired, forecast.end
        )

    @callback
    def _async_expired(self, _now: datetime) -> None:
        """Reevaluate cached forecast bins after the notified interval expires."""
        self._cancel_expiry = None
        self.async_update()

    @callback
    def _dismiss(self) -> None:
        """Remove only this location's precipitation notification."""
        if self._last_notification is not None:
            persistent_notification.async_dismiss(self._hass, self._notification_id)
            self._last_notification = None

    @callback
    def async_close(self) -> None:
        """Release the coordinator subscription and expiry timer when unloading."""
        self._unsubscribe()
        if self._cancel_expiry is not None:
            self._cancel_expiry()
            self._cancel_expiry = None
        self._dismiss()


async def async_setup_precipitation_notifications(
    hass: HomeAssistant,
    entry: BuienalarmConfigEntry,
    coordinator: BuienalarmDataUpdateCoordinator,
) -> None:
    """Load translated messages and start notifications after successful setup."""
    translations = await async_get_translations(
        hass, hass.config.language, "common", {DOMAIN}
    )
    notifications = PrecipitationNotifications(hass, entry, coordinator, translations)
    entry.async_on_unload(notifications.async_close)
    notifications.async_update()
