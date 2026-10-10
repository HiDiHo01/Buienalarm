"""Tests for Buienalarm binary sensors."""

from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN


@pytest.fixture(autouse=True)
def mock_api_calls():
    """Mock API calls to avoid socket connections during tests."""
    with patch("custom_components.buienalarm.api.BuienalarmApiClient.async_get_initial_data", return_value={}), \
         patch("custom_components.buienalarm.api.BuienalarmApiClient.async_get_data", return_value={"data": []}), \
         patch("requests.get"):
        yield


@pytest.mark.asyncio
async def test_binary_sensors_no_precipitation(hass: HomeAssistant) -> None:
    """Test binary sensors when there is no precipitation."""
    now_ts = datetime.now(timezone.utc).timestamp()
    data = {
        "data": [
            {
                "precipitationrate": 0.0,
                "precipitationtype": "rain",
                "timestamp": now_ts,
            }
        ]
    }

    with patch("custom_components.buienalarm.api.BuienalarmApiClient.async_get_data", return_value=data):
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
            entity_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, unique_id)
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

    with patch("custom_components.buienalarm.api.BuienalarmApiClient.async_get_data", return_value=data):
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
        exp_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_precipitation_expected")
        assert exp_id is not None
        assert hass.states.get(exp_id).state == "on"

        # Currently Raining
        rain_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_currently_raining")
        assert rain_id is not None
        assert hass.states.get(rain_id).state == "on"

        # Currently Snowing
        snow_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_currently_snowing")
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

    with patch("custom_components.buienalarm.api.BuienalarmApiClient.async_get_data", return_value=data):
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

        snow_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_currently_snowing")
        assert snow_id is not None
        assert hass.states.get(snow_id).state == "on"

        rain_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_currently_raining")
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

    with patch("custom_components.buienalarm.api.BuienalarmApiClient.async_get_data", return_value=data):
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
        rain_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_currently_raining")
        snow_id = entity_registry.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_currently_snowing")

        assert hass.states.get(rain_id).state == "on"
        assert hass.states.get(snow_id).state == "on"
