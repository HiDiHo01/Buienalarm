"""Exercise threshold notifications through real Home Assistant lifecycle APIs."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components import persistent_notification
from homeassistant.components.persistent_notification import Notification, UpdateType
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.buienalarm.const import DOMAIN

type NotificationEvents = list[tuple[UpdateType, dict[str, Notification]]]


@pytest.fixture
def forecast_api() -> Generator[AsyncMock]:
    """Keep all setup and reload weather requests offline."""
    with (
        patch(
            "custom_components.buienalarm.api.BuienalarmApiClient.async_get_initial_data",
            new_callable=AsyncMock,
            return_value={},
        ),
        patch(
            "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
            new_callable=AsyncMock,
        ) as forecast,
    ):
        yield forecast


@pytest.fixture
def notifications(hass: HomeAssistant) -> Generator[NotificationEvents]:
    """Observe real persistent-notification additions, updates and removals."""
    events: NotificationEvents = []

    @callback
    def receive(update_type: UpdateType, values: dict[str, Notification]) -> None:
        """Capture notifications without reading Home Assistant's private storage."""
        events.append((update_type, dict(values)))

    unsubscribe = persistent_notification.async_register_callback(hass, receive)
    yield events
    unsubscribe()


async def _setup(
    hass: HomeAssistant,
    forecast_api: AsyncMock,
    points: list[object],
    *,
    limit: object = 0,
    options: dict[str, object] | None = None,
    latitude: float = 52.0,
    wrapped: bool = True,
) -> MockConfigEntry:
    """Set up actual platforms and notification subscriptions for one location."""
    payload = {"data": points}
    forecast_api.return_value = {"timeseries": payload} if wrapped else payload
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title="Home",
        data={
            "latitude": latitude,
            "longitude": 5.0,
            "name": "Home",
            "notification_limit": limit,
            "refresh_interval": 3600,
        },
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _point(
    rate: object = 2.5, kind: object = "rain", offset: int = 0
) -> dict[str, object]:
    """Build a forecast point relative to the frozen current UTC time."""
    return {
        "timestamp": datetime.now(timezone.utc).timestamp() + offset,
        "precipitationrate": rate,
        "precipitationtype": kind,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "rate", "expected"),
    [
        (0, 0.0, False),
        (0, 0.0001, True),
        (0, -1.0, False),
        (0, None, False),
        (0, True, False),
        (0, float("nan"), False),
        (0, float("inf"), False),
        (0, "invalid", False),
        (2, 1.9, False),
        (2, 2.0, False),
        (2, 2.0001, True),
        (2, "2,5", True),
        (True, 2.5, False),
        (-1, 2.5, False),
        (float("nan"), 2.5, False),
    ],
)
async def test_notification_threshold_is_strict(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    forecast_api: AsyncMock,
    notifications: NotificationEvents,
    limit: object,
    rate: object,
    expected: bool,
) -> None:
    """Zero means any positive rate; positive thresholds require a greater rate."""
    freezer.move_to("2026-11-01T12:00:00Z")
    await _setup(hass, forecast_api, [_point(rate)], limit=limit)
    assert bool(notifications) is expected
    if expected:
        assert notifications[0][0] == UpdateType.ADDED
        notification = next(iter(notifications[0][1].values()))
        assert "Rain" in notification["message"]
        assert "mm/h" in notification["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language", "kind", "expected_kind", "expected_units"),
    [
        ("en", "rain", "Rain", "mm/h"),
        ("en", " FREEZING RAIN ", "Freezing rain", "mm/h"),
        ("en", "SNOW", "Snow", "mm/h"),
        ("en", "wet snow", "Wet snow", "mm/h"),
        ("en", "mix of rain and snow", "Mixed rain and snow", "mm/h"),
        ("en", "hail", "Unknown type", "mm/h"),
        ("en", None, "Unknown type", "mm/h"),
        ("nl", "rain", "Regen", "mm/u"),
        ("nl", "snow", "Sneeuw", "mm/u"),
        ("nl", "mix", "Mix van regen en sneeuw", "mm/u"),
        ("fr", "rain", "Rain", "mm/h"),
    ],
)
async def test_notification_type_rate_and_time_are_localized(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    forecast_api: AsyncMock,
    notifications: NotificationEvents,
    language: str,
    kind: object,
    expected_kind: str,
    expected_units: str,
) -> None:
    """Create visible translated notifications with the exact API rate and local time."""
    freezer.move_to("2026-11-01T12:00:00Z")
    hass.config.language = language
    await hass.config.async_set_time_zone("Europe/Amsterdam")
    entry = await _setup(hass, forecast_api, [_point(2.5, kind, offset=300)])
    notification_id = f"buienalarm_precipitation_{entry.entry_id}"
    notification = notifications[0][1][notification_id]
    assert notification["title"] == "Buienalarm – Home"
    assert expected_kind in notification["message"]
    assert f"2.5 {expected_units}" in notification["message"]
    assert "2026-11-01 13:05 CET" in notification["message"]


@pytest.mark.asyncio
async def test_options_override_threshold_and_locations_have_separate_notifications(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    forecast_api: AsyncMock,
    notifications: NotificationEvents,
) -> None:
    """Options are authoritative and one location's cleanup cannot dismiss another."""
    freezer.move_to("2026-11-01T12:00:00Z")
    first = await _setup(
        hass, forecast_api, [_point(1.5)], limit=0, options={"notification_limit": 2}
    )
    assert notifications == []
    second = await _setup(
        hass,
        forecast_api,
        [_point(1.5, "snow")],
        latitude=53.0,
        limit=3,
        options={"notification_limit": 0, "name": "Outside"},
    )
    second_id = f"buienalarm_precipitation_{second.entry_id}"
    assert notifications[-1][1][second_id]["title"] == "Buienalarm – Outside"
    first.runtime_data.async_set_updated_data({"data": [_point(3.5)]})
    await hass.async_block_till_done()
    first_id = f"buienalarm_precipitation_{first.entry_id}"
    assert first_id in notifications[-1][1]
    assert first_id != second_id
    assert await hass.config_entries.async_unload(first.entry_id)
    await hass.async_block_till_done()
    assert notifications[-1][0] == UpdateType.REMOVED
    assert set(notifications[-1][1]) == {first_id}


@pytest.mark.asyncio
@pytest.mark.parametrize("wrapped", [False, True])
async def test_updates_deduplicate_and_cleanup_on_failure_recovery_and_unload(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    forecast_api: AsyncMock,
    notifications: NotificationEvents,
    wrapped: bool,
) -> None:
    """Use a stable ID, respect manual dismissal and clean up listeners on unload."""
    freezer.move_to("2026-11-01T12:00:00Z")
    entry = await _setup(hass, forecast_api, [_point()], wrapped=wrapped)
    coordinator = entry.runtime_data
    notification_id = f"buienalarm_precipitation_{entry.entry_id}"
    coordinator.async_set_updated_data({"data": [_point()]})
    await hass.async_block_till_done()
    assert len(notifications) == 1
    persistent_notification.async_dismiss(hass, notification_id)
    await hass.async_block_till_done()
    coordinator.async_set_updated_data({"data": [_point()]})
    await hass.async_block_till_done()
    assert [event[0] for event in notifications] == [
        UpdateType.ADDED,
        UpdateType.REMOVED,
    ]
    coordinator.async_set_updated_data({"data": [_point(3.5, "snow")]})
    await hass.async_block_till_done()
    assert notifications[-1][0] == UpdateType.ADDED
    coordinator.async_set_updated_data({"data": [_point(4.5, "rain")]})
    await hass.async_block_till_done()
    assert notifications[-1][0] == UpdateType.UPDATED
    assert set(notifications[-1][1]) == {notification_id}
    coordinator.async_set_update_error(UpdateFailed("Forecast fetch failed"))
    await hass.async_block_till_done()
    assert notifications[-1][0] == UpdateType.REMOVED
    coordinator.async_set_updated_data({"data": [_point(4.5)]})
    await hass.async_block_till_done()
    assert notifications[-1][0] == UpdateType.ADDED
    coordinator.async_set_updated_data({"data": [_point(0.0)]})
    await hass.async_block_till_done()
    assert notifications[-1][0] == UpdateType.REMOVED
    coordinator.async_set_updated_data({"data": [_point(2.5)]})
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert notifications[-1][0] == UpdateType.REMOVED
    count = len(notifications)
    coordinator.async_set_updated_data({"data": [_point(10.0)]})
    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(hass, datetime.now(timezone.utc))
    await hass.async_block_till_done()
    assert len(notifications) == count


@pytest.mark.asyncio
async def test_cached_forecast_expires_without_network_refresh(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    forecast_api: AsyncMock,
    notifications: NotificationEvents,
) -> None:
    """Choose the earliest usable bin and dismiss it at expiry even with hourly polls."""
    freezer.move_to("2026-11-01T12:00:00Z")
    await _setup(
        hass,
        forecast_api,
        [_point(7.0, "snow", 600), _point(2.5, "rain"), _point(9.0, "snow", -300)],
    )
    assert "Rain" in next(iter(notifications[0][1].values()))["message"]
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass, datetime.now(timezone.utc))
    await hass.async_block_till_done()
    assert notifications[-1][0] == UpdateType.UPDATED
    assert "Snow" in next(iter(notifications[-1][1].values()))["message"]
    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(hass, datetime.now(timezone.utc))
    await hass.async_block_till_done()
    assert notifications[-1][0] == UpdateType.REMOVED
    forecast_api.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_only_forecasts_do_not_create_notifications(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    forecast_api: AsyncMock,
    notifications: NotificationEvents,
) -> None:
    """Malformed or expired timestamps cannot become precipitation alerts."""
    freezer.move_to("2026-11-01T12:00:00Z")
    await _setup(
        hass,
        forecast_api,
        [
            None,
            {},
            {"timestamp": 1e300, "precipitationrate": 2.5},
            {"timestamp": True, "precipitationrate": 2.5},
            _point(2.5, offset=-300),
        ],
    )
    assert notifications == []


@pytest.mark.asyncio
async def test_option_changes_reload_threshold_without_duplicate_subscriptions(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    forecast_api: AsyncMock,
    notifications: NotificationEvents,
) -> None:
    """Changing the configured threshold removes or recreates the same location alert."""
    freezer.move_to("2026-11-01T12:00:00Z")
    entry = await _setup(hass, forecast_api, [_point(2.5)])
    notification_id = f"buienalarm_precipitation_{entry.entry_id}"
    old_coordinator = entry.runtime_data

    hass.config_entries.async_update_entry(entry, options={"notification_limit": 3})
    await hass.async_block_till_done()
    assert entry.runtime_data is not old_coordinator
    assert notifications[-1][0] == UpdateType.REMOVED
    count = len(notifications)
    old_coordinator.async_set_updated_data({"data": [_point(10.0)]})
    await hass.async_block_till_done()
    assert len(notifications) == count

    hass.config_entries.async_update_entry(entry, options={"notification_limit": 2})
    await hass.async_block_till_done()
    assert notifications[-1][0] == UpdateType.ADDED
    assert set(notifications[-1][1]) == {notification_id}
    count = len(notifications)
    entry.runtime_data.async_set_updated_data({"data": [_point(2.5)]})
    await hass.async_block_till_done()
    assert len(notifications) == count
