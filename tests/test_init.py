import pytest
from homeassistant.components.network import async_get_loaded_network, Network
from homeassistant.helpers.typing import HomeAssistantType
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.buienalarm import (
    async_setup_entry,
    async_unload_entry,
    async_reload_entry,
)
from custom_components.buienalarm.const import DOMAIN

# Inject fake network
network_mock = MagicMock(spec=Network)
mock_hass.data["network"] = network_mock

@pytest.fixture
def mock_hass() -> HomeAssistant:
    """Return a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.bus = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass

@pytest.fixture
def mock_entry() -> ConfigEntry:
    """Return a mock ConfigEntry with required 'data' attribute."""
    entry = MagicMock(
        spec=ConfigEntry,
        domain=DOMAIN,
        data={
            "latitude": 52.3676,
            "longitude": 4.9041,
            "network": "test-network",  # Ensure this key is present
        },
        entry_id="test_entry",
        options={},
        title="Test Buienalarm",
    )
    entry.options = {}
    entry.add_update_listener = MagicMock()
    return entry

@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmApiClient")
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry(mock_coordinator_class, mock_client_class, mock_hass, mock_entry):
    """Test successful setup of a config entry."""
    network_mock = MagicMock()
    mock_hass.data = {"network": network_mock}

    mock_coordinator = mock_coordinator_class.return_value
    mock_coordinator.last_update_success = True

    result = await async_setup_entry(mock_hass, mock_entry)

    assert result is True


@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
@pytest.mark.asyncio
async def test_async_setup_entry_failure(mock_coordinator_class, mock_hass, mock_entry):
    """Test setup failure due to unsuccessful data update."""
    mock_coordinator = mock_coordinator_class.return_value
    mock_coordinator.last_update_success = False

    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(mock_hass, mock_entry)

@patch("custom_components.buienalarm.PLATFORMS", ["sensor"])
@pytest.mark.asyncio
async def test_async_unload_entry(mock_hass, mock_entry):
    """Test successful unloading of a config entry."""
    mock_hass.data[DOMAIN] = {mock_entry.entry_id: "coordinator_mock"}

    result = await async_unload_entry(mock_hass, mock_entry)

    assert result is True
    assert mock_entry.entry_id not in mock_hass.data[DOMAIN]

@patch("custom_components.buienalarm.async_setup_entry")
@patch("custom_components.buienalarm.async_unload_entry")
@pytest.mark.asyncio
async def test_async_reload_entry(mock_unload_entry, mock_setup_entry, mock_hass, mock_entry):
    """Test reloading of a config entry."""
    mock_unload_entry.return_value = True
    mock_setup_entry.return_value = True

    await async_reload_entry(mock_hass, mock_entry)

    mock_unload_entry.assert_called_once_with(mock_hass, mock_entry)
    mock_setup_entry.assert_called_once_with(mock_hass, mock_entry)
