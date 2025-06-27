"""Integration tests for Buienalarm sensors."""

from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import async_update_entity
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.const import UnitOfTime, UnitOfVolumetricFlux

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType

from custom_components.buienalarm.const import DOMAIN, SENSORS, DATA_KEY
from custom_components.buienalarm.coordinator import BuienalarmDataUpdateCoordinator

from tests.common import MockConfigEntry


@pytest.mark.asyncio
async def test_sensor_entities_created_and_populated(
    hass: HomeAssistant, mock_buienalarm_data: dict
) -> None:
    """Test all sensors are set up and have correct state and attributes."""

    # Patch the update method to return mock data
    with patch(
        "custom_components.buienalarm.coordinator.BuienalarmDataUpdateCoordinator.async_update_data",
        return_value=mock_buienalarm_data,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Buienalarm Test",
            unique_id="test123",
            data={"latitude": 52.3702, "longitude": 4.8952},  # Amsterdam
        )
        entry.add_to_hass(hass)

        # Start integration
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Check entity registry
    entity_registry = async_get_entity_registry(hass)

    for sensor in SENSORS:
        entity_id = f"sensor.{sensor['key']}"
        state = hass.states.get(entity_id)

        assert state is not None, f"Sensor state missing for {entity_id}"
        assert entity_registry.async_get(entity_id) is not None, f"Entity registry entry missing for {entity_id}"

        expected_value = mock_buienalarm_data.get(sensor["key"])
        if expected_value is None:
            assert state.state == "unknown", f"Expected unknown state for {entity_id}"
        else:
            assert state.state == str(expected_value), f"Unexpected state for {entity_id}: {state.state}"

        # Check attributes
        if sensor["unit_of_measurement"]:
            assert state.attributes.get("unit_of_measurement") == sensor["unit_of_measurement"]
        if sensor["device_class"]:
            assert state.attributes.get("device_class") == sensor["device_class"]
        if sensor["state_class"]:
            assert state.attributes.get("state_class") == sensor["state_class"]
