import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.buienalarm import async_setup_entry, async_unload_entry, async_reload_entry
from custom_components.buienalarm.const import DOMAIN


@pytest.fixture
def mock_hass() -> HomeAssistant:
    """Return a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass


@pytest.fixture
def mock_entry() -> ConfigEntry:
    """Return a mock ConfigEntry."""
    return MagicMock(
        spec=ConfigEntry,
        domain=DOMAIN,
        data={"latitude": 52.3676, "longitude": 4.9041},
        entry_id="test_entry",
        options={},
        title="Test Buienalarm",
    )


@pytest.fixture
def mock_coordinator():
    """Return a mock coordinator."""
    return AsyncMock()


@patch("custom_components.buienalarm.BuienalarmApiClient")
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
@pytest.mark.asyncio
async def test_async_setup_entry(
    mock_coordinator_class, mock_client_class, mock_hass, mock_entry
) -> None:
    """Test successful setup of a config entry."""
    mock_coordinator = mock_coordinator_class.return_value
    mock_coordinator.last_update_success = True

    result = await async_setup_entry(mock_hass, mock_entry)

    assert result is True
    assert DOMAIN in mock_hass.data
    assert mock_entry.entry_id in mock_hass.data[DOMAIN]
    mock_coordinator_class.assert_called_once()


@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
@pytest.mark.asyncio
async def test_async_setup_entry_failure(
    mock_coordinator_class, mock_hass, mock_entry
) -> None:
    """Test setup failure due to unsuccessful data update."""
    mock_coordinator = mock_coordinator_class.return_value
    mock_coordinator.last_update_success = False

    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(mock_hass, mock_entry)


@patch("custom_components.buienalarm.PLATFORMS", ["sensor"])
@pytest.mark.asyncio
async def test_async_unload_entry(mock_hass, mock_entry) -> None:
    """Test successful unloading of a config entry."""
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    mock_hass.data[DOMAIN] = {mock_entry.entry_id: "coordinator_mock"}

    result = await async_unload_entry(mock_hass, mock_entry)

    assert result is True
    assert mock_entry.entry_id not in mock_hass.data[DOMAIN]


@patch("custom_components.buienalarm.async_setup_entry")
@patch("custom_components.buienalarm.async_unload_entry")
@pytest.mark.asyncio
async def test_async_reload_entry(mock_unload_entry, mock_setup_entry, mock_hass, mock_entry) -> None:
    """Test reloading of a config entry."""
    mock_unload_entry.return_value = True
    mock_setup_entry.return_value = True

    result = await async_reload_entry(mock_hass, mock_entry)

    mock_unload_entry.assert_called_once_with(mock_hass, mock_entry)
    mock_setup_entry.assert_called_once_with(mock_hass, mock_entry)

    assert result is True
