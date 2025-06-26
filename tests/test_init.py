"""Tests for the Buienalarm integration setup and teardown."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.network import Network
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.buienalarm import (
    async_setup_entry,
    async_unload_entry,
    async_reload_entry,
)
from custom_components.buienalarm.const import DOMAIN


@pytest.fixture
def mock_hass() -> HomeAssistant:
    """Return a mocked HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.data["network"] = MagicMock(spec=Network)
    hass.bus = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


@pytest.fixture
def mock_entry() -> ConfigEntry:
    """Return a mocked ConfigEntry instance."""
    entry = MagicMock(
        spec=ConfigEntry,
        domain=DOMAIN,
        entry_id="test_entry",
        data={
            "latitude": 52.3676,
            "longitude": 4.9041,
            "network": "test-network",
        },
        title="Test Buienalarm",
    )
    entry.options = {}
    entry.add_update_listener = MagicMock()
    return entry


@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmApiClient")
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_success(
    mock_coordinator_class,
    mock_client_class,
    mock_hass: HomeAssistant,
    mock_entry: ConfigEntry,
) -> None:
    """Test successful async setup of the integration."""
    mock_coordinator = mock_coordinator_class.return_value
    mock_coordinator.last_update_success = True

    result = await async_setup_entry(mock_hass, mock_entry)

    assert result is True
    mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(mock_entry, ["sensor"])


@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_failure(
    mock_coordinator_class,
    mock_hass: HomeAssistant,
    mock_entry: ConfigEntry,
) -> None:
    """Test failed async setup of the integration due to update error."""
    mock_coordinator = mock_coordinator_class.return_value
    mock_coordinator.last_update_success = False

    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(mock_hass, mock_entry)


@pytest.mark.asyncio
@patch("custom_components.buienalarm.PLATFORMS", ["sensor"])
async def test_async_unload_entry(
    mock_hass: HomeAssistant,
    mock_entry: ConfigEntry,
) -> None:
    """Test successful unloading of a config entry."""
    mock_hass.data[DOMAIN] = {mock_entry.entry_id: "mock_coordinator"}

    result = await async_unload_entry(mock_hass, mock_entry)

    assert result is True
    assert mock_entry.entry_id not in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
@patch("custom_components.buienalarm.async_setup_entry", AsyncMock(return_value=True))
@patch("custom_components.buienalarm.async_unload_entry", AsyncMock(return_value=True))
async def test_async_reload_entry(
    mock_unload: AsyncMock,
    mock_setup: AsyncMock,
    mock_hass: HomeAssistant,
    mock_entry: ConfigEntry,
) -> None:
    """Test reloading of the integration."""
    await async_reload_entry(mock_hass, mock_entry)

    mock_unload.assert_called_once_with(mock_hass, mock_entry)
    mock_setup.assert_called_once_with(mock_hass, mock_entry)
