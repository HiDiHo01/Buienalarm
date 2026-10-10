"""Data processor module for Buienalarm API payloads."""

import logging

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


class BuienalarmDataProcessor:
    """Process raw Buienalarm API data into safe sensor values."""

    def __init__(self, raw: object) -> None:
        """Initialize with raw data."""
        self._raw = raw
        self._forecast: list[dict[str, object]] = []

    def process(self) -> dict[str, object]:
        """Process API data into a safe dict for sensors."""
        result: dict[str, object] = {}

        if not isinstance(self._raw, dict):
            _LOGGER.warning(
                "Buienalarm: root is not a dict but %s", type(self._raw).__name__
            )
            return result

        data = self._raw.get("data")
        if isinstance(data, list):
            self._forecast = self._parse_forecast(data)

        result["rain_expected"] = self._has_precipitation()
        result["precipitation_forecast"] = self._forecast
        result["nowcast_message"] = self._parse_nowcast()

        return result

    def _parse_forecast(self, data: list[object]) -> list[dict[str, object]]:
        """Parse each data point into a safe forecast dictionary."""
        forecast: list[dict[str, object]] = []

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue

            rate = item.get("precipitationrate")
            if not isinstance(rate, (int, float)):
                try:
                    rate = float(rate) if rate is not None else 0.0
                except (ValueError, TypeError):
                    continue

            ts_str = item.get("time")
            timestamp = (
                dt_util.parse_datetime(ts_str) if isinstance(ts_str, str) else None
            )
            local_time = dt_util.as_local(timestamp).isoformat() if timestamp else None

            forecast.append(
                {
                    "precipitationrate": round(rate, 2),
                    "precipitationtype": (
                        item.get("precipitationtype")
                        if isinstance(item.get("precipitationtype"), str)
                        else "unknown"
                    ),
                    "timestamp_utc": ts_str or "",
                    "timestamp_local": local_time or "",
                }
            )

        return forecast

    def _has_precipitation(self) -> bool:
        """Check if precipitation > 0.0 mm/h is expected."""
        for item in self._forecast:
            rate = item.get("precipitationrate")
            if isinstance(rate, (int, float)) and rate > 0:
                return True
        return False

    def _parse_nowcast(self) -> dict[str, str]:
        """Extract translated nowcast messages."""
        nowcast = (
            self._raw.get("nowcastmessage") if isinstance(self._raw, dict) else None
        )
        result: dict[str, str] = {}

        if isinstance(nowcast, dict):
            for lang in ("nl", "en", "de"):
                msg = nowcast.get(lang)
                if isinstance(msg, str):
                    result[lang] = msg
        elif isinstance(nowcast, str):
            result["nl"] = nowcast
        return result
