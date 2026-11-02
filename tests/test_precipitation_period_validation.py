"""Regressions for precipitation-period timestamp handling and exposed states."""

from collections import UserDict
from datetime import datetime, timezone, tzinfo
import logging
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN
from custom_components.buienalarm.sensor import BuienalarmSensor


def _sensor(coordinator: MagicMock, key: str) -> BuienalarmSensor:
    """Build a sensor without changing registry identity or platform behavior."""
    return BuienalarmSensor(
        coordinator,
        MockConfigEntry(domain=DOMAIN, data={}),
        name="Forecast",
        unit_of_measurement=None,
        icon=None,
        device_class=None,
        state_class=None,
        key=key,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("timestamp_type", [str, int, float])
@pytest.mark.parametrize("point_type", [dict, UserDict])
@pytest.mark.parametrize("wrapped", [False, True])
async def test_period_and_point_attributes_agree_on_numeric_timestamps(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    timestamp_type: type,
    point_type: type,
    wrapped: bool,
) -> None:
    """Numeric strings without ISO time expose both forecast points and periods."""
    freezer.move_to("2026-11-01T12:00:00Z")
    now_ts = datetime.now(timezone.utc).timestamp()
    points = [
        point_type(
            {"timestamp": timestamp_type(now_ts + offset), "precipitationrate": rate}
        )
        for offset, rate in ((0, 2.0), (300, 4.0), (600, 0.0))
    ]
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.device_info = {}
    coordinator.api_last_updated = None
    payload = {"data": points}
    coordinator.data = {"timeseries": payload} if wrapped else payload
    sensor = _sensor(coordinator, "precipitationrate_total")

    assert sensor.available is True
    assert sensor.native_value is not None
    attributes = sensor.extra_state_attributes
    assert len(attributes["precipitation_data"]) == 3
    assert sensor.get_data("precipitation_periods") == 1
    assert len(attributes["precipitation_periods"]) == 1
    period = attributes["precipitation_periods"][0]
    assert datetime.fromisoformat(period["start"]).timestamp() == now_ts
    assert datetime.fromisoformat(period["stop"]).timestamp() == now_ts + 600
    assert period["duration"] == 10
    assert period["precipitationrate"] == pytest.approx(3.0)
    for point, offset in zip(
        attributes["precipitation_data"], (0, 300, 600), strict=True
    ):
        assert point["timestamp"] == pytest.approx(now_ts + offset)
        assert point["time"].timestamp() == pytest.approx(now_ts + offset)


@pytest.mark.asyncio
@pytest.mark.parametrize("timestamp", [1e300, 1e20])
async def test_out_of_range_period_timestamp_never_reports_zero(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    timestamp: float,
) -> None:
    """Retained finite timestamps outside datetime's range produce unknown state."""
    freezer.move_to("2026-11-01T12:00:00Z")
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.device_info = {}
    coordinator.api_last_updated = None
    coordinator.data = {
        "timeseries": {"data": [{"timestamp": timestamp, "precipitationrate": 1.0}]}
    }
    sensor = _sensor(coordinator, "precipitation_periods")

    with pytest.raises((ValueError, OverflowError, OSError)):
        sensor._get_precipitation_periods_count()
    assert sensor.get_data("precipitation_periods") is None
    assert sensor.native_value is None
    component = EntityComponent(logging.getLogger(__name__), "sensor", hass)
    await component.async_add_entities([sensor])
    assert hass.states.get(sensor.entity_id).state == STATE_UNKNOWN


@pytest.mark.asyncio
@pytest.mark.parametrize("conversion_error", [ValueError, OverflowError, OSError])
async def test_period_timestamp_platform_failures_preserve_unknown(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    monkeypatch: pytest.MonkeyPatch,
    conversion_error: type[Exception],
) -> None:
    """Platform-specific conversion errors follow the documented helper contract."""
    freezer.move_to("2026-11-01T12:00:00Z")
    timestamp = datetime.now(timezone.utc).timestamp() + 300
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.device_info = {}
    coordinator.data = {"data": [{"timestamp": timestamp, "precipitationrate": 1.0}]}
    sensor = _sensor(coordinator, "precipitation_periods")

    def reject_timestamp(value: float, tz: tzinfo | None = None) -> datetime:
        """Simulate a platform rejecting a finite forecast timestamp."""
        raise conversion_error("Unsupported platform timestamp")

    monkeypatch.setattr(
        "custom_components.buienalarm.entity.datetime.fromtimestamp",
        staticmethod(reject_timestamp),
    )
    with pytest.raises(conversion_error):
        sensor._get_precipitation_periods_count()
    assert sensor.native_value is None
