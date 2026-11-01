"""Regression coverage for numeric next-precipitation forecast scans."""

from collections import UserDict
from datetime import datetime, timedelta, timezone, tzinfo
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN
from custom_components.buienalarm.entity import BuienalarmEntity


class ForecastDict(dict):
    """Exercise dictionary subclasses through the safe mapping path."""


class GetOnlyForecast:
    """Represent a supported mapping-like object with only a get method."""

    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def get(self, key: str, default: object = None) -> object:
        """Return a forecast value using the mapping-like protocol."""
        return self.values.get(key, default)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "point_factory", [dict, ForecastDict, UserDict, GetOnlyForecast]
)
@pytest.mark.parametrize("wrapped", [False, True])
async def test_next_precipitation_mapping_formats(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    point_factory: type,
    wrapped: bool,
) -> None:
    """Skip malformed/dry bins and preserve supported forecast mapping formats."""
    freezer.move_to("2026-11-01T12:00:00Z")
    now_ts = datetime.now(timezone.utc).timestamp()
    payload = {
        "data": [
            None,
            "invalid",
            point_factory({"timestamp": True, "precipitationrate": 1.0}),
            point_factory({"timestamp": now_ts - 600, "precipitationrate": 1.0}),
            point_factory({"timestamp": now_ts + 300, "precipitationrate": 0.0}),
            point_factory({"timestamp": now_ts + 600, "precipitationrate": "bad"}),
            point_factory({"timestamp": 1e300, "precipitationrate": 1.0}),
            point_factory({"timestamp": now_ts + 900, "precipitationrate": 2.5}),
        ]
    }
    coordinator = MagicMock()
    coordinator.data = {"timeseries": payload} if wrapped else payload
    entity = BuienalarmEntity(
        coordinator, MockConfigEntry(domain=DOMAIN, data={}), "next_precipitation"
    )

    assert entity.get_next_precipitation() == 15


@pytest.mark.asyncio
@pytest.mark.parametrize("conversion_error", [ValueError, OverflowError, OSError])
async def test_next_precipitation_validates_only_wet_future_bins(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    monkeypatch: pytest.MonkeyPatch,
    conversion_error: type[Exception],
) -> None:
    """Dry scans avoid conversion while platform-invalid wet bins are skipped."""
    freezer.move_to("2026-11-01T12:00:00Z")
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()
    unsupported_timestamp = 253402300799.0
    valid_timestamp = (now + timedelta(minutes=10)).timestamp()
    converted: list[float] = []
    original_fromtimestamp = datetime.fromtimestamp

    def checked_fromtimestamp(timestamp: float, tz: tzinfo | None = None) -> datetime:
        """Record conversion attempts and simulate the platform's timestamp limit."""
        converted.append(timestamp)
        if timestamp == unsupported_timestamp:
            raise conversion_error("Timestamp outside the platform datetime range")
        return original_fromtimestamp(timestamp, tz=tz)

    monkeypatch.setattr(
        "custom_components.buienalarm.entity.datetime.fromtimestamp",
        staticmethod(checked_fromtimestamp),
    )
    forecast = [
        {"timestamp": now_ts + 300, "precipitationrate": rate}
        for rate in (0.0, -1.0, None, True, "bad", float("nan"))
    ]
    coordinator = MagicMock()
    coordinator.data = {"timeseries": {"data": forecast}}
    entity = BuienalarmEntity(
        coordinator, MockConfigEntry(domain=DOMAIN, data={}), "next_precipitation"
    )

    assert entity.get_next_precipitation() is None
    assert converted == []

    forecast.extend(
        [
            {"timestamp": unsupported_timestamp, "precipitationrate": 1.0},
            {"timestamp": valid_timestamp, "precipitationrate": 2.5},
        ]
    )
    assert entity.get_next_precipitation() == 10
    assert converted == [unsupported_timestamp, valid_timestamp]
