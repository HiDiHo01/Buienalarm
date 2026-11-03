"""Regression coverage for forecast availability and unknown precipitation types."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN
from custom_components.buienalarm.sensor import BuienalarmSensor


async def _setup_forecast(
    hass: HomeAssistant, points: list[dict[str, object]]
) -> MockConfigEntry:
    """Load real platforms with an offline, successfully refreshed forecast."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        title="Availability test",
        data={"latitude": 52.0, "longitude": 5.0},
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.buienalarm.api.BuienalarmApiClient.async_get_initial_data",
            return_value={},
        ),
        patch(
            "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
            return_value={"data": points},
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.runtime_data.last_update_success
    return entry


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("key", "expected"), [("next_precipitation", 5), ("precipitation_periods", 1)]
)
async def test_forecast_availability_and_values_accept_comma_decimal_rates(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    key: str,
    expected: int,
) -> None:
    """Comma-decimal forecasts remain available and yield their calculated values."""
    freezer.move_to("2026-11-03T12:00:00Z")
    now_ts = datetime.now(timezone.utc).timestamp()
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts + offset,
                "precipitationrate": "1,2",
                "precipitationtype": "rain",
            }
            for offset in (300, 600)
        ]
    }
    sensor = BuienalarmSensor(
        coordinator,
        MockConfigEntry(domain=DOMAIN, data={}),
        name="Forecast",
        unit_of_measurement=None,
        icon=None,
        device_class=None,
        state_class=None,
        key=key,
    )

    assert sensor.available is True
    assert sensor.native_value == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("rate", [0.0, 2.5])
@pytest.mark.parametrize("raw_type", [None, "unknown", "hail", 42, [], {}])
async def test_unknown_type_hides_only_wet_description(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    rate: float,
    raw_type: object,
) -> None:
    """Keep numeric and type states while withholding an unsupported wet description."""
    freezer.move_to("2026-11-03T12:00:00Z")
    point: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).timestamp(),
        "precipitationrate": rate,
    }
    if raw_type is not None:
        point["precipitationtype"] = raw_type
    entry = await _setup_forecast(hass, [point])
    registry = async_get_entity_registry(hass)
    expected_states = {
        "precipitationrate_now_desc": "unavailable" if rate > 0 else "Geen neerslag",
        "precipitationtype_now": "Onbekend" if rate > 0 else "Geen neerslag",
    }
    for key, expected_state in expected_states.items():
        entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"{entry.entry_id}_{key}"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == expected_state
    numeric_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_precipitationrate_now"
    )
    assert numeric_id is not None
    numeric_state = hass.states.get(numeric_id)
    assert numeric_state is not None
    assert float(numeric_state.state) == pytest.approx(rate)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raw_type", "expected"),
    [
        (" RAIN ", "Matige regen"),
        ("FREEZING RAIN", "Matige regen"),
        (" Snow ", "Matige sneeuw"),
        ("wet snow", "Matige sneeuw"),
        ("mix", "Matige regen en sneeuw"),
        ("mix of rain and snow", "Matige regen en sneeuw"),
    ],
)
async def test_recognized_types_keep_current_description_available(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    raw_type: str,
    expected: str,
) -> None:
    """Normalize recognized API types consistently with the displayed description."""
    freezer.move_to("2026-11-03T12:00:00Z")
    entry = await _setup_forecast(
        hass,
        [
            {
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "precipitationrate": 2.5,
                "precipitationtype": raw_type,
            }
        ],
    )
    registry = async_get_entity_registry(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_precipitationrate_now_desc"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("offset", "expected_states"),
    [
        (0, ("on", "on", "off")),
        (-299, ("on", "on", "off")),
        (-300, ("unavailable", "unavailable", "unavailable")),
        (300, ("on", "unavailable", "unavailable")),
    ],
)
async def test_binary_sensor_availability_requires_matching_forecast_coverage(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    offset: int,
    expected_states: tuple[str, str, str],
) -> None:
    """Expose unavailable states for expired bins and missing current-bin coverage."""
    freezer.move_to("2026-11-03T12:00:00Z")
    entry = await _setup_forecast(
        hass,
        [
            {
                "timestamp": datetime.now(timezone.utc).timestamp() + offset,
                "precipitationrate": 2.5,
                "precipitationtype": "rain",
            }
        ],
    )
    registry = async_get_entity_registry(hass)
    for key, expected_state in zip(
        ("precipitation_expected", "currently_raining", "currently_snowing"),
        expected_states,
        strict=True,
    ):
        entity_id = registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_{key}"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == expected_state
