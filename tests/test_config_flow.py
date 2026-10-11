"""Test Buienalarm config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN


@pytest.fixture(autouse=True)
def mock_setup_entry():
    """Mock config entry setup for config flow tests."""
    mock_resp = AsyncMock()
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.status = 200
    mock_resp.reason = "OK"
    mock_resp.headers = {}
    mock_resp.json = AsyncMock(return_value={"data": []})
    mock_resp.raise_for_status = MagicMock()

    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp

    with patch("aiohttp.ClientSession.get", return_value=mock_resp), patch(
        "custom_components.buienalarm.async_get_clientsession",
        return_value=mock_session,
    ):
        yield


@pytest.mark.asyncio
async def test_config_flow_user_step_success(hass: HomeAssistant) -> None:
    """Test successful user step in config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    user_input = {
        CONF_NAME: "Amsterdam",
        CONF_LATITUDE: 52.3702,
        CONF_LONGITUDE: 4.8952,
    }

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Amsterdam (52.3702, 4.8952)"
    assert result2["data"][CONF_LATITUDE] == 52.3702
    assert result2["data"][CONF_LONGITUDE] == 4.8952

    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_config_flow_invalid_coordinates(hass: HomeAssistant) -> None:
    """Test invalid coordinates in config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    user_input = {
        CONF_NAME: "Invalid",
        CONF_LATITUDE: 999.0,
        CONF_LONGITUDE: 4.8952,
    }

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_coordinates"}


@pytest.mark.asyncio
async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Amsterdam",
        unique_id="52.3702_4.8952",
        data={CONF_LATITUDE: 52.3702, CONF_LONGITUDE: 4.8952},
        options={"refresh_interval": 300},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Amsterdam",
            CONF_LATITUDE: 52.3702,
            CONF_LONGITUDE: 4.8952,
            "notification_limit": 1,
            "refresh_interval": 600,
        },
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["refresh_interval"] == 600
