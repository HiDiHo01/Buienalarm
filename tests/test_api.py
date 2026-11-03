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


@pytest.mark.asyncio
async def test_async_get_initial_data_success(hass: HomeAssistant) -> None:
    """Test that async_get_initial_data returns data when request succeeds."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.json = AsyncMock(return_value={"success": True, "grid": "52.37_4.89"})
    mock_session.get.return_value.__aenter__.return_value = mock_response

    client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass)
    data = await client.async_get_initial_data()

    assert data == {"success": True, "grid": "52.37_4.89"}
    mock_response.json.assert_awaited_once_with(content_type=None)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_payload", [[], None, "invalid", 123])
async def test_async_get_initial_data_non_dict_response(
    hass: HomeAssistant, invalid_payload: object
) -> None:
    """Test that async_get_initial_data raises ApiError when JSON payload is not a dictionary."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.json = AsyncMock(return_value=invalid_payload)
    mock_session.get.return_value.__aenter__.return_value = mock_response

    client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass)

    with pytest.raises(
        ApiError, match="Invalid initial data format: expected dictionary"
    ):
        await client.async_get_initial_data()


@pytest.mark.asyncio
async def test_async_get_initial_data_timeout(hass: HomeAssistant) -> None:
    """Test that async_get_initial_data raises ApiError on timeout."""
    mock_session = MagicMock()

    class PendingContextManager:
        async def __aenter__(self):
            await asyncio.sleep(10)

        async def __aexit__(self, exc_type, exc, tb):
            pass

    mock_session.get.return_value = PendingContextManager()

    client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass, timeout=0.01)

    with pytest.raises(
        ApiError, match="Timeout while requesting Buienalarm initial data"
    ):
        await client.async_get_initial_data()


@pytest.mark.asyncio
async def test_async_get_initial_data_http_error(hass: HomeAssistant) -> None:
    """Test that async_get_initial_data raises ApiError on non-200 HTTP status."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.reason = "Internal Server Error"
    mock_session.get.return_value.__aenter__.return_value = mock_response

    client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass)

    with pytest.raises(ApiError, match="HTTP error 500: Internal Server Error"):
        await client.async_get_initial_data()


@pytest.mark.asyncio
async def test_async_get_initial_data_client_error(hass: HomeAssistant) -> None:
    """Test that async_get_initial_data raises ApiError on client connection error."""
    import aiohttp

    mock_session = MagicMock()
    mock_session.get.side_effect = aiohttp.ClientError("Connection refused")

    client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass)

    with pytest.raises(ApiError, match="Connection refused"):
        await client.async_get_initial_data()


@pytest.mark.asyncio
async def test_async_get_initial_data_invalid_json(hass: HomeAssistant) -> None:
    """Test that async_get_initial_data raises ApiError on invalid JSON response."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(side_effect=ValueError("Expecting value"))
    mock_session.get.return_value.__aenter__.return_value = mock_response

    client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass)

    with pytest.raises(ApiError, match="Invalid JSON"):
        await client.async_get_initial_data()
