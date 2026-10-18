"""Tests for Buienalarm binary sensors."""

from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN
from custom_components.buienalarm.binary_sensor import async_setup_entry
from custom_components.buienalarm.coordinator import BuienalarmDataUpdateCoordinator
from custom_components.buienalarm.sensor_types import BINARY_SENSOR_DESCRIPTIONS


async def test_setup_uses_runtime_coordinator(hass: HomeAssistant) -> None:
    """Set up every binary sensor using only the entry's runtime coordinator."""
    entry = MockConfigEntry(domain=DOMAIN)
    coordinator = Mock(spec=BuienalarmDataUpdateCoordinator)
    coordinator.data = {}
    coordinator.device_info = {}
    coordinator.last_update_success = True
    entry.runtime_data = coordinator
    async_add_entities = Mock()

    await async_setup_entry(hass, entry, async_add_entities)

    async_add_entities.assert_called_once()
    entities = list(async_add_entities.call_args.args[0])
    assert len(entities) == len(BINARY_SENSOR_DESCRIPTIONS)
    assert all(entity.coordinator is coordinator for entity in entities)


@pytest.mark.parametrize("runtime_unset", [True, False])
async def test_setup_rejects_legacy_coordinator(
    hass: HomeAssistant, runtime_unset: bool
) -> None:
    """Keep the explicit error when runtime data is missing despite legacy data."""
    entry = MockConfigEntry(domain=DOMAIN)
    if not runtime_unset:
        entry.runtime_data = None
    hass.data[DOMAIN] = {entry.entry_id: Mock(spec=BuienalarmDataUpdateCoordinator)}
    async_add_entities = Mock()

    with pytest.raises(RuntimeError) as exc_info:
        await async_setup_entry(hass, entry, async_add_entities)

    assert str(exc_info.value) == (
        f"Buienalarm coordinator is not available for config entry {entry.entry_id}"
    )
    async_add_entities.assert_not_called()


@pytest.fixture(autouse=True)
def mock_api_calls():
    """Mock API calls to avoid socket connections during tests."""
    with patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_initial_data",
        return_value={},
    ), patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
        return_value={"data": []},
    ), patch(
        "requests.get"
    ):
        yield


@pytest.mark.asyncio
async def test_binary_sensors_no_precipitation(hass: HomeAssistant) -> None:
    """Test binary sensors when there is no precipitation or only historical rain."""
    now_ts = datetime.now(timezone.utc).timestamp()
    data = {
        "data": [
            {
                "precipitationrate": 2.5,
                "precipitationtype": "rain",
                "timestamp": now_ts - 600,
            },
            {
                "precipitationrate": 0.0,
                "precipitationtype": "rain",
                "timestamp": now_ts,
            },
        ]
    }

    with patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
        return_value=data,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Buienalarm Test",
            unique_id="test_no_precip",
            data={"latitude": 52.3702, "longitude": 4.8952},
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_registry = async_get_entity_registry(hass)

        for key in ("precipitation_expected", "currently_raining", "currently_snowing"):
            unique_id = f"{entry.entry_id}_{key}"
            entity_id = entity_registry.async_get_entity_id(
                "binary_sensor", DOMAIN, unique_id
            )
            assert entity_id is not None
            state = hass.states.get(entity_id)
            assert state is not None
            assert state.state == "off"


@pytest.mark.asyncio
async def test_binary_sensors_raining_now(hass: HomeAssistant) -> None:
    """Test currently_raining and precipitation_expected binary sensors."""
    now_ts = datetime.now(timezone.utc).timestamp()
    data = {
        "data": [
            {
                "precipitationrate": 1.5,
                "precipitationtype": "  RAIN ",
                "timestamp": now_ts,
            }
        ]
    }

    with patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
        return_value=data,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Buienalarm Test Raining",
            unique_id="test_raining",
            data={"latitude": 52.3702, "longitude": 4.8952},
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_registry = async_get_entity_registry(hass)

        # Expected
        exp_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_precipitation_expected"
        )
        assert exp_id is not None
        assert hass.states.get(exp_id).state == "on"

        # Currently Raining
        rain_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_currently_raining"
        )
        assert rain_id is not None
        assert hass.states.get(rain_id).state == "on"

        # Currently Snowing
        snow_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_currently_snowing"
        )
        assert snow_id is not None
        assert hass.states.get(snow_id).state == "off"


@pytest.mark.asyncio
async def test_binary_sensors_snowing_now(hass: HomeAssistant) -> None:
    """Test currently_snowing binary sensor."""
    now_ts = datetime.now(timezone.utc).timestamp()
    data = {
        "data": [
            {
                "precipitationrate": 2.0,
                "precipitationtype": "SNOW",
                "timestamp": now_ts,
            }
        ]
    }

    with patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
        return_value=data,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Buienalarm Test Snowing",
            unique_id="test_snowing",
            data={"latitude": 52.3702, "longitude": 4.8952},
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_registry = async_get_entity_registry(hass)

        snow_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_currently_snowing"
        )
        assert snow_id is not None
        assert hass.states.get(snow_id).state == "on"

        rain_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_currently_raining"
        )
        assert rain_id is not None
        assert hass.states.get(rain_id).state == "off"


@pytest.mark.asyncio
async def test_binary_sensors_nested_timeseries_data(hass: HomeAssistant) -> None:
    """Test binary sensors with nested timeseries data structure."""
    now_ts = datetime.now(timezone.utc).timestamp()
    data = {
        "timeseries": {
            "data": [
                {
                    "precipitationrate": "1,2",
                    "precipitationtype": "mix",
                    "timestamp": now_ts,
                }
            ]
        }
    }

    with patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
        return_value=data,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Buienalarm Test Nested",
            unique_id="test_nested",
            data={"latitude": 52.3702, "longitude": 4.8952},
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_registry = async_get_entity_registry(hass)

        # Mix counts for both rain and snow
        rain_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_currently_raining"
        )
        snow_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_currently_snowing"
        )

        assert hass.states.get(rain_id).state == "on"
        assert hass.states.get(snow_id).state == "on"


@pytest.mark.asyncio
async def test_binary_sensors_empty_data_list(hass: HomeAssistant) -> None:
    """Test binary sensors remain available and off when API returns an empty data list."""
    with patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
        return_value={"data": []},
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Buienalarm Test Empty Data List",
            unique_id="test_empty_data_list",
            data={"latitude": 52.3702, "longitude": 4.8952},
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_registry = async_get_entity_registry(hass)

        for key in ("precipitation_expected", "currently_raining", "currently_snowing"):
            unique_id = f"{entry.entry_id}_{key}"
            entity_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
            assert entity_id is not None
            state = hass.states.get(entity_id)
            assert state is not None
            assert state.state == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize("unclassified_type", [None, "unknown", "hail"])
async def test_binary_sensor_precipitation_expected_unclassified_type(
    hass: HomeAssistant,
    unclassified_type: str | None,
) -> None:
    """Test precipitation_expected turns on for positive rate even with unclassified precipitationtype."""
    now_ts = datetime.now(timezone.utc).timestamp()
    period = {
        "precipitationrate": 1.5,
        "timestamp": now_ts + 300,
    }
    if unclassified_type is not None:
        period["precipitationtype"] = unclassified_type

    data = {"data": [period]}

    with patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
        return_value=data,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Buienalarm Test Unclassified Type",
            unique_id=f"test_unclassified_{unclassified_type}",
            data={"latitude": 52.3702, "longitude": 4.8952},
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_registry = async_get_entity_registry(hass)

        exp_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_precipitation_expected"
        )
        assert exp_id is not None
        assert hass.states.get(exp_id).state == "on"

        rain_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_currently_raining"
        )
        snow_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_currently_snowing"
        )
        assert hass.states.get(rain_id).state == "off"
        assert hass.states.get(snow_id).state == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_payload",
    [
        {"data": "invalid"},
        {
            "data": [
                {
                    "precipitationrate": 1.5,
                    "precipitationtype": "rain",
                    "timestamp": "invalid_timestamp",
                }
            ]
        },
    ],
)
async def test_binary_sensors_missing_or_invalid_data(
    hass: HomeAssistant,
    data_payload: dict,
) -> None:
    """Test binary sensors when precipitation data or period timestamp is missing/unparseable."""
    with patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
        return_value=data_payload,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Buienalarm Test Invalid Data",
            unique_id="test_invalid_data",
            data={"latitude": 52.3702, "longitude": 4.8952},
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_registry = async_get_entity_registry(hass)

        for key in ("precipitation_expected", "currently_raining", "currently_snowing"):
            unique_id = f"{entry.entry_id}_{key}"
            entity_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
            assert entity_id is not None
            state = hass.states.get(entity_id)
            assert state is not None
            assert state.state == "unknown"


@pytest.mark.asyncio
async def test_binary_sensors_freezing_rain_now(hass: HomeAssistant) -> None:
    """Test currently_raining is on and currently_snowing is off for freezing rain."""
    now_ts = datetime.now(timezone.utc).timestamp()
    data = {
        "data": [
            {
                "precipitationrate": 1.8,
                "precipitationtype": "freezing rain",
                "timestamp": now_ts,
            }
        ]
    }

    with patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
        return_value=data,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Buienalarm Test Freezing Rain",
            unique_id="test_freezing_rain",
            data={"latitude": 52.3702, "longitude": 4.8952},
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_registry = async_get_entity_registry(hass)

        exp_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_precipitation_expected"
        )
        rain_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_currently_raining"
        )
        snow_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_currently_snowing"
        )

        assert hass.states.get(exp_id).state == "on"
        assert hass.states.get(rain_id).state == "on"
        assert hass.states.get(snow_id).state == "off"
