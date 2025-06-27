"""Tests for Buienalarm sensors."""

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.helpers.entity_component import async_update_entity
from homeassistant.const import UnitOfTime, UnitOfVolumetricFlux

from custom_components.buienalarm.const import DOMAIN, SENSORS


@pytest.mark.asyncio
async def test_sensors_created_and_populated(hass: HomeAssistant, mock_buienalarm_data: dict) -> None:
    """Test that all Buienalarm sensors are created with correct values."""

    # Inject test data into hass.data
    hass.data[DOMAIN] = mock_buienalarm_data

    # Setup sensor platform
    assert await async_setup_component(hass, "sensor", {
        "sensor": {
            "platform": DOMAIN,
            "name": "Test Buienalarm",
        }
    })

    await hass.async_block_till_done()

    # Loop through sensors and validate states
    for sensor in SENSORS:
        entity_id = f"sensor.{sensor['key']}"
        state = hass.states.get(entity_id)

        assert state is not None, f"Sensor not found: {entity_id}"

        expected = mock_buienalarm_data.get(sensor["key"])
        assert state.state in (str(expected), "unknown"), f"Unexpected state for {entity_id}"

        # Validate unit, device class and state class
        if sensor["unit_of_measurement"]:
            assert state.attributes.get("unit_of_measurement") == sensor["unit_of_measurement"]
        if sensor["device_class"]:
            assert state.attributes.get("device_class") == sensor["device_class"]
        if sensor["state_class"]:
            assert state.attributes.get("state_class") == sensor["state_class"]
