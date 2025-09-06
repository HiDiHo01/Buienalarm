import pytest
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN, SENSORS


@pytest.fixture(autouse=True)
def mock_requests():
    """Prevent real HTTP calls by mocking requests.get with nested 'data' key."""
    with patch("requests.get") as mock_get:
        mock_resp = mock_get.return_value
        inner = {
            sensor["key"]: (
                3.14 if sensor.get("device_class") or sensor.get("state_class") else "Test message"
            )
            for sensor in SENSORS
        }
        mock_resp.json.return_value = {"data": inner}
        yield


@pytest.fixture(autouse=True)
def mock_aiohttp_get():
    """Mock aiohttp.ClientSession.get for Buienalarm."""
    inner = {
        sensor["key"]: (
            3.14 if sensor.get("device_class") or sensor.get("state_class") else "Test message"
        )
        for sensor in SENSORS
    }

    async def _mock_json():
        return {"data": inner}

    mock_resp = AsyncMock()
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.status = 200
    mock_resp.json = _mock_json

    with patch("aiohttp.ClientSession.get", return_value=mock_resp):
        yield


@pytest.mark.asyncio
async def test_sensor_entities_created_and_populated(
    hass: HomeAssistant,
) -> None:
    """Ensure sensors are created and reflect mocked coordinator data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Test",
        unique_id="test123",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = async_get_entity_registry(hass)

    # Build expected data directly from SENSORS mock
    expected_data = {
        sensor["key"]: (
            3.14 if sensor.get("device_class") or sensor.get("state_class") else "Test message"
        )
        for sensor in SENSORS
    }

    # Verify all sensors exist and have correct state/attributes
    for sensor in SENSORS:
        unique_id = f"{entry.unique_id}_{sensor['key']}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None, f"Entity for {sensor['name']} not found"

        state = hass.states.get(entity_id)
        assert state is not None, f"State for {entity_id} missing"

        expected = expected_data[sensor["key"]]
        if isinstance(expected, float):
            assert float(state.state) == expected
        else:
            assert state.state == expected

        # Attributes check
        for attr in ("unit_of_measurement", "device_class", "state_class"):
            if sensor.get(attr):
                assert state.attributes.get(attr) == sensor[attr]

    # ---- guard: invalid data structure ----
    bad_resp = AsyncMock()
    bad_resp.__aenter__.return_value = bad_resp
    bad_resp.status = 200
    bad_resp.json = AsyncMock(return_value=[])

    with patch("aiohttp.ClientSession.get", return_value=bad_resp):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    for sensor in SENSORS:
        unique_id = f"{entry.unique_id}_{sensor['key']}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "unknown"
