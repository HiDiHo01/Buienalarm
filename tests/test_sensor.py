import pytest
from unittest.mock import patch
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN, SENSORS

@pytest.fixture(autouse=True)
def mock_requests(monkeypatch):
    """Prevent real HTTP calls by mocking requests.get at module level."""
    with patch("requests.get") as mock_get:
        mock_resp = mock_get.return_value
        mock_resp.json.return_value = {key: "test_value" for key in [s["key"] for s in SENSORS]}
        yield

@patch(
    "custom_components.buienalarm.coordinator.BuienalarmDataUpdateCoordinator._async_update_data"
)
@pytest.mark.asyncio
async def test_sensor_entities_created_and_populated(
    mock_update, hass: HomeAssistant, mock_buienalarm_data: dict
) -> None:
    """Test all sensors are set up and have correct state and attributes using mock coordinator data."""
    # Configure the coordinator to return our test data
    mock_update.return_value = mock_buienalarm_data

    # Create and add config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Test",
        unique_id="test123",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )
    entry.add_to_hass(hass)

    # Initialize integration
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = async_get_entity_registry(hass)

    for sensor in SENSORS:
        entity_id = f"sensor.{sensor['key']}"
        state = hass.states.get(entity_id)

        assert state, f"Sensor state missing for {entity_id}"
        assert entity_registry.async_get(entity_id), (
            f"Entity registry entry missing for {entity_id}"
        )

        expected = mock_buienalarm_data.get(sensor["key"])
        if expected is None:
            assert state.state == "unknown", f"Expected unknown for {entity_id}"
        else:
            assert state.state == str(expected), (
                f"Unexpected state for {entity_id}: {state.state}"
            )

        # Verify attributes
        for attr in ("unit_of_measurement", "device_class", "state_class"):
            if sensor.get(attr):
                assert state.attributes.get(attr) == sensor[attr], (
                    f"Wrong {attr} for {entity_id}"
                )
