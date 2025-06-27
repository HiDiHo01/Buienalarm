"""Test initialization of the Buienalarm integration."""

import pytest
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm import (
    async_setup_entry,
    async_unload_entry,
    async_reload_entry,
)
from custom_components.buienalarm.const import DOMAIN, CONF_LATITUDE, CONF_LONGITUDE


@pytest.fixture
def config_data() -> dict:
    """Provide minimal valid config entry data."""
    return {
        CONF_LATITUDE: 52.1,
        CONF_LONGITUDE: 5.1,
    }


@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_success(mock_coordinator, hass: HomeAssistant, config_data: dict) -> None:
    """Test successful setup of config entry."""
    coordinator = mock_coordinator.return_value
    coordinator.last_update_success = True

    entry = MockConfigEntry(domain=DOMAIN, data=config_data, options={})
    entry.add_to_hass(hass)

    result = await async_setup_entry(hass, entry)

    assert result is True
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]
    assert hass.data[DOMAIN][entry.entry_id] is coordinator


@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_failure(mock_coordinator, hass: HomeAssistant, config_data: dict) -> None:
    """Test setup fails if coordinator update was unsuccessful."""
    coordinator = mock_coordinator.return_value
    coordinator.last_update_success = False

    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
    entry.add_to_hass(hass)

    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
@patch("custom_components.buienalarm.PLATFORMS", ["sensor"])
async def test_async_unload_entry(hass: HomeAssistant, config_data: dict) -> None:
    """Test successful unloading of an entry."""
    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
    entry.add_to_hass(hass)

    hass.data[DOMAIN] = {entry.entry_id: AsyncMock()}

    with patch("homeassistant.config_entries.ConfigEntries.async_unload_platforms", return_value=True):
        result = await async_unload_entry(hass, entry)

    assert result is True
    assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.asyncio
@patch("custom_components.buienalarm.async_setup_entry", new_callable=AsyncMock)
@patch("custom_components.buienalarm.async_unload_entry", new_callable=AsyncMock)
async def test_async_reload_entry(mock_unload, mock_setup, hass: HomeAssistant) -> None:
    """Test config entry reload."""
    entry = MockConfigEntry(domain=DOMAIN, data={
        CONF_LATITUDE: 52.1,
        CONF_LONGITUDE: 5.1,
    })
    entry.add_to_hass(hass)

    await async_reload_entry(hass, entry)

    mock_unload.assert_called_once_with(hass, entry)
    mock_setup.assert_called_once_with(hass, entry)
