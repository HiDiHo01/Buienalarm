"""Test initialization of the Buienalarm integration."""

import pytest

from custom_components.buienalarm.const import DOMAIN
from custom_components.buienalarm import async_setup_entry, async_unload_entry

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant


@pytest.fixture
def config_data() -> dict:
    """Return minimal valid config for Buienalarm."""
    return {"station": "utrecht"}


@pytest.mark.asyncio
async def test_async_setup_entry_success(hass: HomeAssistant, config_data: dict) -> None:
    """Test successful async_setup_entry of the integration."""
    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
    entry.add_to_hass(hass)

    result = await async_setup_entry(hass, entry)

    assert result is True
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_setup_entry_failure(
    hass: HomeAssistant, config_data: dict, monkeypatch
) -> None:
    """Test setup entry fails gracefully if coordinator fails."""
    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
    entry.add_to_hass(hass)

    monkeypatch.setattr(
        "custom_components.buienalarm.BuienalarmDataUpdateCoordinator.async_config_entry_first_refresh",
        lambda self: (_ for _ in ()).throw(Exception("fail")),
    )

    with pytest.raises(Exception):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_async_unload_entry(hass: HomeAssistant, config_data: dict) -> None:
    """Test unloading an entry."""
    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
    entry.add_to_hass(hass)

    await async_setup_entry(hass, entry)
    assert DOMAIN in hass.data

    result = await async_unload_entry(hass, entry)

    assert result is True
    assert entry.entry_id not in hass.data[DOMAIN]
