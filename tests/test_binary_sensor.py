"""Test Buienalarm binary sensor platform."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN
from custom_components.buienalarm.sensor_types import BINARY_SENSOR_DESCRIPTIONS


@pytest.fixture(autouse=True)
def mock_aiohttp_get():
    """Mock aiohttp.ClientSession.get for Buienalarm API."""
    now_ts = int(time.time())
    payload = {
        "data": [
            {
                "precipitationrate": 2.5,
                "precipitationtype": "rain",
                "time": "2026-05-05T12:00:00Z",
                "timestamp": now_ts,
            }
        ],
        "nowcastmessage": {"nl": "Regen"},
    }

    mock_resp = AsyncMock()
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.status = 200
    mock_resp.reason = "OK"
    mock_resp.headers = {"Age": "10"}
    mock_resp.json = AsyncMock(return_value=payload)
    mock_resp.raise_for_status = MagicMock()

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch("aiohttp.ClientSession.get", return_value=mock_resp), patch(
        "custom_components.buienalarm.async_get_clientsession",
        return_value=mock_session,
    ):
        yield mock_resp


@pytest.mark.asyncio
async def test_binary_sensor_entities_created_and_populated(
    hass: HomeAssistant,
) -> None:
    """Ensure binary sensors are created and reflect rainfall state."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Test",
        unique_id="52.3702_4.8952",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = async_get_entity_registry(hass)

    for desc in BINARY_SENSOR_DESCRIPTIONS:
        unique_id = f"{entry.unique_id}_{desc.key}"
        entity_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, unique_id
        )
        assert entity_id is not None, f"Binary entity for {desc.key} not found"

        state = hass.states.get(entity_id)
        assert state is not None, f"State for {entity_id} missing"
        assert state.state in ("on", "off")

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
