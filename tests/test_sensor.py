import pytest
from unittest.mock import patch
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN, SENSORS

@pytest.fixture(autouse=True)
def mock_requests(monkeypatch):
    """Prevent real HTTP calls by mocking requests.get with nested 'data' key."""
    with patch("requests.get") as mock_get:
        mock_resp = mock_get.return_value
        # Provide float-compatible values for numeric sensors and strings for others
        inner = {}
        for sensor in SENSORS:
            key = sensor["key"]
            if sensor.get("device_class") or sensor.get("state_class"):
                inner[key] = 3.14
            else:
                inner[key] = "Test message"
        mock_resp.json.return_value = {"data": inner}
        yield

@pytest.mark.asyncio
async def test_sensor_entities_created_and_populated(hass: HomeAssistant) -> None:
    """Ensure sensors are created and reflect mocked coordinator data."""
    # Expected extracted data from nested structure
    expected_data = {}
    for sensor in SENSORS:
        key = sensor["key"]
        if sensor.get("device_class") or sensor.get("state_class"):
            expected_data[key] = 3.14
        else:
            expected_data[key] = "Test message"

    # Create config entry and initialize integration
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Test",
        unique_id="test123",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Explicit check for nowcastmessage sensor
    state_now = hass.states.get("sensor.nowcastmessage")
    assert state_now is not None, "Sensor nowcastmessage missing"
    assert state_now.state == expected_data["nowcastmessage"], (
        f"Expected '{expected_data['nowcastmessage']}' for nowcastmessage, got {state_now.state}"
    )

    entity_registry = async_get_entity_registry(hass)

    for sensor in SENSORS:
        entity_id = f"sensor.{sensor['key']}"
        state = hass.states.get(entity_id)
        # Entity should exist
        assert state is not None, f"Missing sensor {entity_id}"
        assert entity_registry.async_get(entity_id) is not None, f"Registry missing {entity_id}"

        expected = expected_data[sensor["key"]]
        if isinstance(expected, float):
            # numeric sensor should parse float
            assert float(state.state) == expected, f"Expected numeric value {expected} for {entity_id}"
        else:
            # non-numeric sensors use string
            assert state.state == expected, f"Expected string value '{expected}' for {entity_id}"

        # Verify optional attributes
        for attr in ("unit_of_measurement", "device_class", "state_class"):
            if sensor.get(attr):
                assert state.attributes.get(attr) == sensor[attr], (
                    f"Wrong {attr} for {entity_id}"
                )

    # Confirm guard: integration should handle missing 'data' key gracefully
    # Simulate coordinator returning non-dict
    with patch("requests.get") as bad_get:
        bad_resp = bad_get.return_value
        bad_resp.json.return_value = []  # incorrect structure
        # Reload integration to trigger fetch
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    # After bad data, all sensor states should be 'unknown'
    for sensor in SENSORS:
        entity_id = f"sensor.{sensor['key']}"
        state = hass.states.get(entity_id)
        assert state.state == "unknown", f"Expected unknown for bad data on {entity_id}"
