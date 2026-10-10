import logging

from homeassistant.util import dt as dt_util
from homeassistant.util.dt import as_local

_LOGGER = logging.getLogger(__name__)


class BuienalarmDataProcessor:
    """Verwerkt ruwe Buienalarm API data naar bruikbare sensorwaarden."""

    def __init__(self, raw: object) -> None:
        """Initialiseer met ruwe data (object)."""
        self._raw = raw
        self._forecast: list[dict[str, object]] = []

    def process(self) -> dict[str, object]:
        """
        Verwerk API-data naar een veilig dict voor sensors.

        Verwachte structuur:
        {
            "data": [
                {
                    "precipitationrate": float,
                    "precipitationtype": str,
                    "timestamp": int (epoch UTC),
                    "time": str (ISO UTC),
                },
                ...
            ],
            "nowcastmessage": {
                "nl": str,
                "en": str,
                "de": str,
            }
        }
        """
        result: dict[str, object] = {}

        if not isinstance(self._raw, dict):
            _LOGGER.warning("Buienalarm: root is geen dict maar %s", type(self._raw).__name__)
            return result

        data = self._raw.get("data")
        if isinstance(data, list):
            self._forecast = self._parse_forecast(data)
        else:
            _LOGGER.debug("Buienalarm: ontbrekende of ongeldige 'data' (type: %s)", type(data).__name__)

        result["rain_expected"] = self._has_precipitation()
        result["precipitation_forecast"] = self._forecast
        result["nowcast_message"] = self._parse_nowcast()

        return result

    def _parse_forecast(self, data: list[object]) -> list[dict[str, object]]:
        """Verwerk elk datapunt in forecast naar veilige dict."""
        forecast: list[dict[str, object]] = []

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                _LOGGER.debug("Buienalarm: overgeslagen datapunt [%s], geen dict: %s", i, item)
                continue

            rate = item.get("precipitationrate")
            if not isinstance(rate, (int, float)):
                try:
                    rate = float(rate)
                except (ValueError, TypeError):
                    _LOGGER.debug("Buienalarm: ongeldig 'precipitationrate': %s", rate)
                    continue

            ts_str = item.get("time")
            timestamp = dt_util.parse_datetime(ts_str) if isinstance(ts_str, str) else None
            local_time = as_local(timestamp).isoformat() if timestamp else None

            forecast.append(
                {
                    "precipitationrate": round(rate, 2),
                    "precipitationtype": item.get("precipitationtype") if isinstance(item.get("precipitationtype"), str) else "unknown",
                    "timestamp_utc": ts_str or "",
                    "timestamp_local": local_time or "",
                }
            )

        return forecast

    def _has_precipitation(self) -> bool:
        """Controleer of er neerslag wordt verwacht boven 0.0 mm/h."""
        for item in self._forecast:
            rate = item.get("precipitationrate")
            if isinstance(rate, (int, float)) and rate > 0:
                return True
        return False

    def _parse_nowcast(self) -> dict[str, str]:
        """Extract vertaalde nowcast boodschap, fallback op lege string."""
        nowcast = self._raw.get("nowcastmessage")
        result: dict[str, str] = {}

        if isinstance(nowcast, dict):
            for lang in ("nl", "en", "de"):
                msg = nowcast.get(lang)
                if isinstance(msg, str):
                    result[lang] = msg
        return result
