import logging
from datetime import datetime

from homeassistant.util import dt as dt_util
from homeassistant.util.dt import as_local

_LOGGER = logging.getLogger(__name__)


class BuienalarmDataProcessor:
    """Verwerkt ruwe Buienalarm API data naar bruikbare sensorwaarden."""

    def __init__(self, raw: object) -> None:
        """Initialiseer met ruwe data (object)."""
        self._raw = raw
        self._forecast: list[dict[str, object]] = []
        self._rain_expected: bool = False

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
        rain_expected = False

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

            # Bolt optimization: track precipitation expectation during parse loop to avoid second pass
            if rate > 0:
                rain_expected = True

            ts_str = item.get("time")
            timestamp = None
            if isinstance(ts_str, str):
                # Bolt optimization: datetime.fromisoformat is ~2x faster than dt_util.parse_datetime for ISO strings
                try:
                    timestamp = datetime.fromisoformat(ts_str)
                except ValueError:
                    timestamp = dt_util.parse_datetime(ts_str)

            local_time = as_local(timestamp).isoformat() if timestamp else None
            ptype = item.get("precipitationtype")

            forecast.append(
                {
                    "precipitationrate": round(rate, 2),
                    "precipitationtype": ptype if isinstance(ptype, str) else "unknown",
                    "timestamp_utc": ts_str or "",
                    "timestamp_local": local_time or "",
                }
            )

        self._rain_expected = rain_expected
        return forecast

    def _has_precipitation(self) -> bool:
        """Controleer of er neerslag wordt verwacht boven 0.0 mm/h."""
        # Bolt optimization: return tracked boolean computed during _parse_forecast
        return self._rain_expected

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
