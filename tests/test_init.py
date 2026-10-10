"""Test initialization of the Buienalarm integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.buienalarm.const import DOMAIN


@pytest.fixture
def config_data() -> dict[str, float | str]:
    """Provide minimal valid config entry data."""
    return {
        CONF_LATITUDE: 52.1,
        CONF_LONGITUDE: 5.1,
        "network": "home",
    }


@pytest.mark.asyncio
@patch("custom_components.buienalarm.async_get_clientsession")
@patch("custom_components.buienalarm.BuienalarmApiClient")
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_success(
    mock_coordinator_cls: MagicMock,
    mock_api_cls: MagicMock,
    mock_get_clientsession: MagicMock,
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test successful setup of config entry."""
    coordinator = mock_coordinator_cls.return_value
    coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)
    coordinator.last_update_success = True
    coordinator.data = {"data": []}
    coordinator.device_info = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, "test")},
        name="Test",
    )

    entry = MockConfigEntry(
        domain=DOMAIN, data=config_data, options={}, unique_id="52.1_5.1"
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert entry.state == ConfigEntryState.LOADED
    assert entry.runtime_data is coordinator
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]
    assert hass.data[DOMAIN][entry.entry_id] is coordinator

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
@patch("custom_components.buienalarm.async_get_clientsession")
@patch("custom_components.buienalarm.BuienalarmApiClient")
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_failure(
    mock_coordinator_cls: MagicMock,
    mock_api_cls: MagicMock,
    mock_get_clientsession: MagicMock,
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test setup fails if coordinator update was unsuccessful."""
    coordinator = mock_coordinator_cls.return_value
    coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=UpdateFailed("Fetch failed")
    )

    entry = MockConfigEntry(domain=DOMAIN, data=config_data, unique_id="52.1_5.1")
    entry.add_to_hass(hass)

    with pytest.raises(ConfigEntryNotReady, match="Failed to fetch initial data"):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
@patch("custom_components.buienalarm.async_get_clientsession")
@patch("custom_components.buienalarm.BuienalarmApiClient")
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
@patch("custom_components.buienalarm.PLATFORMS", ["sensor"])
async def test_async_unload_entry(
    mock_coordinator_cls: MagicMock,
    mock_api_cls: MagicMock,
    mock_get_clientsession: MagicMock,
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test successful unloading of an entry."""
    coordinator = mock_coordinator_cls.return_value
    coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)
    coordinator.last_update_success = True
    coordinator.data = {"data": []}
    coordinator.device_info = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, "test")},
        name="Test",
    )

    entry = MockConfigEntry(domain=DOMAIN, data=config_data, unique_id="52.1_5.1")
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await async_unload_entry(hass, entry)

    assert result is True
    assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
@patch(
    "homeassistant.config_entries.ConfigEntries.async_reload", new_callable=AsyncMock
)
async def test_async_reload_entry(
    mock_async_reload: AsyncMock,
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test config entry reload."""
    entry = MockConfigEntry(domain=DOMAIN, data=config_data, unique_id="52.1_5.1")
    entry.add_to_hass(hass)

    await async_reload_entry(hass, entry)
    mock_async_reload.assert_called_once_with(entry.entry_id)


@pytest.mark.asyncio
@patch("custom_components.buienalarm.async_get_clientsession")
@patch("custom_components.buienalarm.BuienalarmApiClient")
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_exception(
    mock_coordinator_cls: MagicMock,
    mock_api_cls: MagicMock,
    mock_get_clientsession: MagicMock,
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test setup fails due to unexpected exception in coordinator."""
    mock_coordinator_cls.side_effect = Exception("Unexpected failure")

    entry = MockConfigEntry(domain=DOMAIN, data=config_data, unique_id="52.1_5.1")
    entry.add_to_hass(hass)

    with pytest.raises(ConfigEntryNotReady, match="Failed to create coordinator"):
        await async_setup_entry(hass, entry)
