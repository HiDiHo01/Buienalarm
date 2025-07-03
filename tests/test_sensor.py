import pytest
from unittest.mock import patch
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.util import slugify
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN, SENSORS

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

@pytest.mark.asyncio
async def test_sensor_entities_created_and_populated(hass: HomeAssistant) -> None:
    """Ensure sensors are created and reflect mocked coordinator data."""
    expected_data = {
        sensor["key"]: (3.14 if sensor.get("device_class") or sensor.get("state_class") else "Test message")
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

    # ---- expliciete check voor nowcastmessage ----
    nowcast_entity_id = (
        f"sensor.{slugify(entry.title)}_nowcastmessage"
    )
    state_now = hass.states.get(nowcast_entity_id)
    assert state_now is not None, f"Sensor {nowcast_entity_id} ontbreekt"
    assert state_now.state == expected_data["nowcastmessage"], (
        f"Verwacht '{expected_data['nowcastmessage']}' voor {nowcast_entity_id}, "
        f"kreeg '{state_now.state}'"
    )

    entity_registry = async_get_entity_registry(hass)

    for sensor in SENSORS:
        entity_id = (
            f"sensor.{slugify(entry.title)}_{sensor['key']}"
        )
        state = hass.states.get(entity_id)

        assert state is not None, f"Sensor {entity_id} ontbreekt"
        assert entity_registry.async_get(entity_id) is not None, f"Registry mist {entity_id}"

        expected = expected_data[sensor["key"]]
        if isinstance(expected, float):
            assert float(state.state) == expected, f"Verwacht {expected} (float) voor {entity_id}"
        else:
            assert state.state == expected, f"Verwacht '{expected}' (str) voor {entity_id}"

        for attr in ("unit_of_measurement", "device_class", "state_class"):
            if sensor.get(attr):
                assert state.attributes.get(attr) == sensor[attr], f"Foutieve {attr} voor {entity_id}"

    # ---- guard: onjuiste data structuur ----
    with patch("requests.get") as bad_get:
        bad_resp = bad_get.return_value
        bad_resp.json.return_value = []  # verkeerde structuur
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    for sensor in SENSORS:
        entity_id = f"sensor.{slugify(sensor['name'])}"
        state = hass.states.get(entity_id)
        assert state.state == "unknown", f"Verwacht 'unknown' bij onjuiste data voor {entity_id}"
