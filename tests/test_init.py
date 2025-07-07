"""Test initialization of the Buienalarm integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm import (
    async_setup_entry,
    async_unload_entry,
    async_reload_entry,
)
from custom_components.buienalarm.const import DOMAIN, PLATFORMS

@pytest.fixture
def config_data() -> dict[str, float | str]:
    """Provide minimal valid config entry data."""
    return {
        CONF_LATITUDE: 52.1,
        CONF_LONGITUDE: 5.1,
        "network": "home",
    }

@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_success(mock_coordinator: AsyncMock, hass: HomeAssistant, config_data: dict[str, float | str]) -> None:
    """Test successful setup of config entry."""
    coordinator = mock_coordinator.return_value
    coordinator.last_update_success = True

    entry = MockConfigEntry(domain=DOMAIN, data=config_data, options={})
    entry.add_to_hass(hass)

    # Test full setup
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify results
    # assert result is True
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]
    assert hass.data[DOMAIN][entry.entry_id] is coordinator
    assert PLATFORMS[0] in hass.config.components
    assert "sensor" in hass.config.components

@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_failure(mock_coordinator: AsyncMock, hass: HomeAssistant, config_data: dict[str, float | str]) -> None:
    """Test setup fails if coordinator update was unsuccessful."""
    coordinator = mock_coordinator.return_value
    coordinator.last_update_success = False

    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
    entry.add_to_hass(hass)

    with pytest.raises(ConfigEntryNotReady, match=r"Failed to initialize Mock Title"):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
@patch("custom_components.buienalarm.PLATFORMS", ["sensor"]) # test dynamische platformen.
async def test_async_unload_entry(mock_coordinator: AsyncMock, hass: HomeAssistant, config_data: dict[str, float | str]) -> None:
    """Test successful unloading of an entry."""
    coordinator = mock_coordinator.return_value
    coordinator.last_update_success = True

    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
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
@patch("custom_components.buienalarm.async_setup_entry", new_callable=AsyncMock)
@patch("custom_components.buienalarm.async_unload_entry", new_callable=AsyncMock)
async def test_async_reload_entry(
    mock_unload: AsyncMock,
    mock_setup: AsyncMock,
    hass: HomeAssistant,
) -> None:
    """Test config entry reload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_LATITUDE: 52.1,
            CONF_LONGITUDE: 5.1,
        },
    )
    entry.add_to_hass(hass)

    await async_reload_entry(hass, entry)

    mock_unload.assert_called_once_with(hass, entry)
    mock_setup.assert_called_once_with(hass, entry)

@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_exception(mock_coordinator: AsyncMock, hass: HomeAssistant, config_data: dict[str, float | str]) -> None:
    """Test setup fails due to unexpected exception in coordinator."""
    mock_coordinator.side_effect = Exception("Unexpected failure")

    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
    entry.add_to_hass(hass)

    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, entry)
