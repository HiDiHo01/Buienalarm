import logging
from unittest.mock import AsyncMock, MagicMock
import pytest
from homeassistant.core import HomeAssistant

from custom_components.buienalarm.api import BuienalarmApiClient
from custom_components.buienalarm.exceptions import ApiError


import asyncio
from aiohttp import ClientTimeout


@pytest.mark.asyncio
async def test_async_get_nowcast_timeout(hass: HomeAssistant) -> None:
    """Test that async_get_nowcast raises ApiError when request times out."""
    mock_session = MagicMock()

    class PendingContextManager:
        async def __aenter__(self):
            await asyncio.sleep(10)

        async def __aexit__(self, exc_type, exc, tb):
            pass

    mock_session.get.return_value = PendingContextManager()

    client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass)

    with pytest.raises(ApiError, match="Timeout while requesting Buienalarm data"):
        await client.async_get_nowcast(timeout=ClientTimeout(total=0.01))


@pytest.mark.asyncio
async def test_async_get_nowcast_logging_optimization(hass: HomeAssistant) -> None:
    """Test that async_get_nowcast succeeds both when debug logging is enabled and disabled."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json", "Age": "10"}
    mock_response.json = AsyncMock(
        return_value={
            "data": [{"precipitationrate": 0.5}],
            "nowcastmessage": {"nl": "Regen"},
        }
    )
    mock_session.get.return_value.__aenter__.return_value = mock_response

    client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass)

    # Test with debug logging disabled (normal HA state)
    logger = logging.getLogger("custom_components.buienalarm.api")
    logger.setLevel(logging.INFO)
    res_info = await client.async_get_nowcast()
    assert "timeseries" in res_info
    assert res_info["timeseries"]["nowcastmessage"]["nl"] == "Regen"

    # Test with debug logging enabled
    logger.setLevel(logging.DEBUG)
    res_debug = await client.async_get_nowcast()
    assert "timeseries" in res_debug
    assert res_debug["timeseries"]["nowcastmessage"]["nl"] == "Regen"
