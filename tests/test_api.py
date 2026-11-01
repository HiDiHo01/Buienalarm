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
@pytest.mark.parametrize(
    "invalid_payload",
    [
        [],
        None,
        "invalid",
        123,
        {},
        {"data": None},
        {"data": "invalid"},
        {"data": []},
        {"data": [123]},
        {"data": [None]},
    ],
)
async def test_async_get_nowcast_invalid_structure(
    hass: HomeAssistant, invalid_payload: object
) -> None:
    """Test that async_get_nowcast raises ApiError when JSON payload is not a valid container."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {}
    mock_response.json = AsyncMock(return_value=invalid_payload)
    mock_session.get.return_value.__aenter__.return_value = mock_response

    client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass)

    with pytest.raises(ApiError):
        await client.async_get_nowcast()


@pytest.mark.asyncio
async def test_async_get_nowcast_fixtures(
    hass: HomeAssistant, nowcast_payload: dict, user_sample_payload: dict
) -> None:
    """Test that async_get_nowcast succeeds with both recorded API fixtures."""
    for fixture_payload in (nowcast_payload, user_sample_payload):
        mock_session = MagicMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "application/json", "Age": "0"}
        mock_response.json = AsyncMock(return_value=fixture_payload)
        mock_session.get.return_value.__aenter__.return_value = mock_response

        client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass)
        res = await client.async_get_nowcast()
        assert res["timeseries"] == fixture_payload
        assert "retrieval_time" in res
        assert "cache_age" in res


@pytest.mark.asyncio
async def test_coordinator_handles_invalid_api_response_and_recovers(
    hass: HomeAssistant, nowcast_payload: dict
) -> None:
    """Test that coordinator handles invalid API response, preserves last good data and api_last_updated, and recovers."""
    from custom_components.buienalarm.coordinator import (
        BuienalarmDataUpdateCoordinator,
    )
    from homeassistant.helpers.entity import DeviceInfo
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.headers = {"Content-Type": "application/json", "Age": "5"}
    mock_response.json = AsyncMock(return_value=nowcast_payload)
    mock_session.get.return_value.__aenter__.return_value = mock_response

    entry = MockConfigEntry(
        domain="buienalarm", data={"latitude": 52.37, "longitude": 4.89}
    )
    entry.add_to_hass(hass)

    client = BuienalarmApiClient(52.3702, 4.8951, mock_session, hass)
    coordinator = BuienalarmDataUpdateCoordinator(
        hass=hass,
        api=client,
        device_info=DeviceInfo(identifiers={("buienalarm", entry.entry_id)}),
        config_entry=entry,
    )

    # 1. Successful first update
    await coordinator.async_refresh()
    assert coordinator.last_update_success is True
    initial_data = coordinator.data
    assert initial_data is not None
    initial_last_updated = coordinator.api_last_updated
    assert initial_last_updated is not None

    # 2. Subsequent update returns invalid payload (empty data list)
    mock_response.json = AsyncMock(return_value={"data": []})
    await coordinator.async_refresh()
    assert coordinator.last_update_success is False
    assert coordinator.data == initial_data
    assert coordinator.api_last_updated == initial_last_updated

    # 3. Recovery with valid payload
    mock_response.json = AsyncMock(return_value=nowcast_payload)
    await coordinator.async_refresh()
    assert coordinator.last_update_success is True
    assert coordinator.data is not None
    assert coordinator.api_last_updated is not None
    assert coordinator.api_last_updated >= initial_last_updated


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
