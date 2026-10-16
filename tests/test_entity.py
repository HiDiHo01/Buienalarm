"""Unit tests for historical filtering in precipitation period calculations."""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN
from custom_components.buienalarm.entity import BuienalarmEntity


@pytest.fixture
def now_utc() -> Iterator[datetime]:
    """Freeze the entity clock at a fractional second to exercise cutoff precision."""
    now = datetime(2026, 5, 5, 12, 0, 0, 250000, tzinfo=timezone.utc)
    with patch("custom_components.buienalarm.entity.datetime", wraps=datetime) as clock:
        clock.now.return_value = now
        yield now


@pytest.fixture
def period_entity(hass: HomeAssistant) -> BuienalarmEntity:
    """Create an entity with coordinator data controlled by each unit test."""
    coordinator = MagicMock()
    coordinator.hass = hass
    coordinator.data = {"data": []}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Precipitation periods",
        unique_id="period_filter_test",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )
    return BuienalarmEntity(coordinator, entry, "precipitation_periods")


@pytest.mark.parametrize(
    ("offset_seconds", "expected_duration"),
    [
        pytest.param(-301, None, id="expired"),
        pytest.param(-300.125, None, id="just-before-cutoff"),
        pytest.param(-300, None, id="exact-cutoff"),
        pytest.param(-299.875, 14, id="just-after-cutoff"),
        pytest.param(-120, 12, id="active-bin"),
        pytest.param(0, 10, id="starts-now"),
        pytest.param(300, 5, id="future-bin"),
    ],
)
def test_precipitation_period_five_minute_cutoff(
    period_entity: BuienalarmEntity,
    now_utc: datetime,
    offset_seconds: int | float,
    expected_duration: int | None,
) -> None:
    """Include a wet bin only while its five-minute interval has not expired."""
    start = now_utc + timedelta(seconds=offset_seconds)
    stop = now_utc + timedelta(minutes=10)
    period_entity.coordinator.data = {
        "data": [
            {"timestamp": start.timestamp(), "precipitationrate": 2.5},
            {"timestamp": stop.timestamp(), "precipitationrate": 0},
        ]
    }

    periods = period_entity._get_precipitation_periods()

    if expected_duration is None:
        assert periods == []
    else:
        assert periods == [
            {
                "start": start,
                "stop": stop,
                "duration_minutes": expected_duration,
                "precipitationrate": pytest.approx(2.5),
            }
        ]


@pytest.mark.parametrize("rate", [0, 4.5], ids=["dry", "wet"])
@pytest.mark.parametrize(
    "timestamp",
    [
        pytest.param(1777978800, id="integer"),
        pytest.param(1777978800.125, id="fractional"),
        pytest.param(-(10**20), id="outside-datetime-range"),
    ],
)
def test_historical_bins_skip_datetime_conversion(
    period_entity: BuienalarmEntity,
    now_utc: datetime,
    timestamp: int | float,
    rate: int | float,
) -> None:
    """Expired bins need no datetime allocation, even outside datetime's range."""
    period_entity.coordinator.data = {
        "data": [{"timestamp": timestamp, "precipitationrate": rate}]
    }
    with patch("custom_components.buienalarm.entity.datetime", wraps=datetime) as clock:
        clock.now.return_value = now_utc

        assert period_entity._get_precipitation_periods() == []
        clock.fromtimestamp.assert_not_called()


def test_historical_bins_do_not_affect_period_grouping_or_averages(
    period_entity: BuienalarmEntity, now_utc: datetime
) -> None:
    """Ignore expired wet and dry bins while preserving separate forecast periods."""
    period_entity.coordinator.data = {
        "timeseries": {
            "data": [
                {"timestamp": now_utc.timestamp() - 600, "precipitationrate": 100},
                {"timestamp": now_utc.timestamp() - 120, "precipitationrate": 3},
                {"timestamp": now_utc.timestamp() - 300, "precipitationrate": 0},
                {"timestamp": now_utc.timestamp() + 180, "precipitationrate": 1},
                {"timestamp": now_utc.timestamp() + 480, "precipitationrate": 0},
                {"timestamp": now_utc.timestamp() + 780, "precipitationrate": 0.2},
                {"timestamp": now_utc.timestamp() + 1080, "precipitationrate": 0.3},
                {"timestamp": now_utc.timestamp() + 1380, "precipitationrate": 0.5},
                {"timestamp": now_utc.timestamp() + 1680, "precipitationrate": 0},
            ]
        },
        "retrieval_time": now_utc,
        "cache_age": 0,
    }

    assert period_entity._get_precipitation_periods() == [
        {
            "start": now_utc - timedelta(minutes=2),
            "stop": now_utc + timedelta(minutes=8),
            "duration_minutes": 10,
            "precipitationrate": pytest.approx(2),
        },
        {
            "start": now_utc + timedelta(minutes=13),
            "stop": now_utc + timedelta(minutes=28),
            "duration_minutes": 15,
            "precipitationrate": pytest.approx(0.33),
        },
    ]


@pytest.mark.parametrize("historical_rate", [0, 100], ids=["dry", "wet"])
@pytest.mark.parametrize(
    ("wet_bins", "expected_duration", "expected_rate"),
    [(1, 0, 1), (2, 5, 2)],
    ids=["single-bin", "multiple-bins"],
)
def test_trailing_historical_bin_does_not_move_open_period_end(
    period_entity: BuienalarmEntity,
    now_utc: datetime,
    historical_rate: int,
    wet_bins: int,
    expected_duration: int,
    expected_rate: int,
) -> None:
    """An expired trailing record must not replace the last retained forecast time."""
    period_entity.coordinator.data = {
        "data": [
            {
                "timestamp": now_utc.timestamp() + index * 300,
                "precipitationrate": 1 + index * 2,
            }
            for index in range(wet_bins)
        ]
        + [
            {
                "timestamp": now_utc.timestamp() - 600,
                "precipitationrate": historical_rate,
            }
        ]
    }

    assert period_entity._get_precipitation_periods() == [
        {
            "start": now_utc,
            "stop": now_utc + timedelta(minutes=expected_duration),
            "duration_minutes": expected_duration,
            "precipitationrate": pytest.approx(expected_rate),
        }
    ]


@pytest.mark.parametrize(
    "timestamp", [None, True, False, "1777982400", "invalid", [], {}]
)
def test_invalid_timestamp_is_skipped_before_numeric_comparison(
    period_entity: BuienalarmEntity, now_utc: datetime, timestamp: object
) -> None:
    """Malformed timestamps must not raise or alter a valid precipitation period."""
    period_entity.coordinator.data = {
        "data": [
            {"timestamp": now_utc.timestamp(), "precipitationrate": 2},
            {"timestamp": timestamp, "precipitationrate": 100},
            {"timestamp": now_utc.timestamp() + 300, "precipitationrate": 0},
        ]
    }

    assert period_entity._get_precipitation_periods() == [
        {
            "start": now_utc,
            "stop": now_utc + timedelta(minutes=5),
            "duration_minutes": 5,
            "precipitationrate": pytest.approx(2),
        }
    ]


def test_retained_period_uses_local_timezone(
    period_entity: BuienalarmEntity, now_utc: datetime
) -> None:
    """Filtering by UTC epoch must preserve local, timezone-aware period endpoints."""
    local_zone = ZoneInfo("Europe/Amsterdam")
    period_entity.coordinator.data = {
        "data": [
            {"timestamp": int(now_utc.timestamp()) - 300, "precipitationrate": 100},
            {"timestamp": int(now_utc.timestamp()), "precipitationrate": 2},
            {"timestamp": int(now_utc.timestamp()) + 300, "precipitationrate": 0},
        ]
    }

    with patch.object(dt, "DEFAULT_TIME_ZONE", local_zone):
        periods = period_entity._get_precipitation_periods()

    assert len(periods) == 1
    assert periods[0]["start"].isoformat() == "2026-05-05T14:00:00+02:00"
    assert periods[0]["stop"].isoformat() == "2026-05-05T14:05:00+02:00"
    assert periods[0]["duration_minutes"] == 5
    assert periods[0]["precipitationrate"] == pytest.approx(2)
