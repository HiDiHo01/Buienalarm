import pytest
from unittest.mock import AsyncMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.util import slugify
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN, SENSORS

def get_entity_id(sensor_name: str) -> str:
    """Return registry entity_id by the sensor’s true unique_id."""
    unique_id = f"{slugify(sensor_name)}_none"          # 👈 location slug is 'none'
    entity_id = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        unique_id,
    )
    assert entity_id is not None, f"entity_id not found for {unique_id}"
    return entity_id

@pytest.fixture(autouse=True)
def mock_requests(monkeypatch):
    """Prevent real HTTP calls by mocking requests.get with nested 'data' key."""
    with patch("requests.get") as mock_get:
        mock_resp = mock_get.return_value
        inner = {
            sensor["key"]: (3.14 if sensor.get("device_class") or sensor.get("state_class") else "Test message")
            for sensor in SENSORS
        }
        mock_resp.json.return_value = {"data": inner}
        yield

@pytest.fixture(autouse=True)
def mock_aiohttp_get():
    """Mock aiohttp.ClientSession.get for Buienalarm."""
    inner = {
        sensor["key"]: (
            3.14
            if sensor.get("device_class") or sensor.get("state_class")
            else "Test message"
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
async def test_sensor_entities_created_and_populated(hass: HomeAssistant) -> None:
    """Ensure sensors are created and reflect mocked coordinator data."""
    expected_data = {
        sensor["key"]: (
            3.14
            if sensor.get("device_class") or sensor.get("state_class")
            else "Test message"
        )
        for sensor in SENSORS
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Test",
        unique_id="test123",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = async_get_entity_registry(hass)

    def get_entity_id(key: str) -> str:
        """Return entity_id via registry from unique_id."""
        entity_id = entity_registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            f"{entry.unique_id}_{key}",
        )
        assert entity_id is not None, f"entity_id not found for key {key}"
        return entity_id

    # ---- expliciete check voor nowcastmessage ----
    # nowcast_entity_id = get_entity_id("nowcastmessage")
    nowcast_entity_id = get_entity_id("Buienalarm") 
    state_now = hass.states.get(nowcast_entity_id)
    assert state_now is not None, f"Sensor {nowcast_entity_id} ontbreekt"
    assert state_now.state == expected_data["nowcastmessage"]

    # ---- overige sensoren ----
    for sensor in SENSORS:
        # entity_id = get_entity_id(sensor["key"])
        entity_id = get_entity_id(sensor["name"])
        state = hass.states.get(entity_id)

        assert state is not None, f"Sensor {entity_id} ontbreekt"

        expected = expected_data[sensor["key"]]
        if isinstance(expected, float):
            assert float(state.state) == expected
        else:
            assert state.state == expected

        for attr in ("unit_of_measurement", "device_class", "state_class"):
            if sensor.get(attr):
                assert state.attributes.get(attr) == sensor[attr]

    # ---- guard: onjuiste data structuur ----
    with patch("aiohttp.ClientSession.get", return_value=AsyncMock(json=lambda: [])):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    for sensor in SENSORS:
        entity_id = get_entity_id(sensor["key"])
        state = hass.states.get(entity_id)
        assert state.state == "unknown"
