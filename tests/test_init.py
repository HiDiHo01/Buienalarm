"""Test initialization of the Buienalarm integration."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm import (
    async_migrate_entity_unique_ids,
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
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


@pytest.fixture(autouse=True)
def mock_api_calls():
    """Mock API calls to avoid socket error during test_async_reload_entry."""
    with (
        patch(
            "custom_components.buienalarm.api.BuienalarmApiClient.async_get_initial_data",
            return_value={},
        ),
        patch(
            "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
            return_value={"data": []},
        ),
    ):
        yield


@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_success(
    mock_coordinator: AsyncMock,
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test successful setup of config entry."""
    coordinator = mock_coordinator.return_value
    coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)
    coordinator.last_update_success = True

    entry = MockConfigEntry(domain=DOMAIN, data=config_data, options={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert entry.runtime_data is coordinator
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]
    assert hass.data[DOMAIN][entry.entry_id] is coordinator
    assert set(PLATFORMS).intersection(hass.config.components)


@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_failure(
    mock_coordinator: AsyncMock,
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test setup fails if coordinator update was unsuccessful."""
    coordinator = mock_coordinator.return_value
    coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=ConfigEntryNotReady("Failed to fetch initial data for Mock Title")
    )
    coordinator.last_update_success = False

    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
    entry.add_to_hass(hass)

    with pytest.raises(ConfigEntryNotReady, match="Failed to fetch initial data"):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
@patch("custom_components.buienalarm.PLATFORMS", ["sensor"])  # test dynamic platforms
async def test_async_unload_entry(
    mock_coordinator: AsyncMock,
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test successful unloading of an entry."""
    coordinator = mock_coordinator.return_value
    coordinator.async_config_entry_first_refresh = AsyncMock(return_value=None)
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
async def test_refresh_interval_update_interval(
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test that coordinator update_interval matches refresh_interval from options or data."""
    # 1. Custom refresh_interval in options (600 seconds)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        options={"refresh_interval": 600},
        unique_id="test_refresh_opt",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.update_interval == timedelta(seconds=600)

    # Clean up
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # 2. Custom refresh_interval in data (450 seconds), no options
    data_with_refresh = {
        CONF_LATITUDE: 52.2,
        CONF_LONGITUDE: 5.2,
        "refresh_interval": 450,
    }
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data=data_with_refresh,
        options={},
        unique_id="test_refresh_data",
    )
    entry2.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()
    coordinator2 = hass.data[DOMAIN][entry2.entry_id]
    assert coordinator2.update_interval == timedelta(seconds=450)


@pytest.mark.asyncio
async def test_async_reload_entry(
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test config entry reload."""
    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_reload:
        await async_reload_entry(hass, entry)
        mock_reload.assert_called_once_with(entry.entry_id)


@pytest.mark.asyncio
@patch("custom_components.buienalarm.BuienalarmDataUpdateCoordinator")
async def test_async_setup_entry_exception(
    mock_coordinator: AsyncMock,
    hass: HomeAssistant,
    config_data: dict[str, float | str],
) -> None:
    """Test setup fails due to unexpected exception in coordinator."""
    mock_coordinator.side_effect = Exception("Unexpected failure")

    entry = MockConfigEntry(domain=DOMAIN, data=config_data)
    entry.add_to_hass(hass)

    with pytest.raises(ConfigEntryNotReady, match="Failed to create coordinator"):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_setup_entry_options_missing_from_data(hass: HomeAssistant) -> None:
    """Test setup succeeds when coordinates are present in entry.options but missing in entry.data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "Options Only Location"},
        options={
            "name": "Options Only Location",
            CONF_LATITUDE: 52.5,
            CONF_LONGITUDE: 4.8,
        },
        unique_id="options_only",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.data[CONF_LATITUDE] == 52.5
    assert entry.data[CONF_LONGITUDE] == 4.8
    assert entry.unique_id == "52.5_4.8"
    assert entry.title == "Options Only Location (52.5, 4.8)"


@pytest.mark.asyncio
async def test_setup_entry_updates_identity_when_options_change(
    hass: HomeAssistant,
) -> None:
    """Test setup updates entry data, unique_id, and title when options have new coordinates."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Old Location",
            CONF_LATITUDE: 51.0,
            CONF_LONGITUDE: 4.0,
            "location_id": "51.0_4.0",
            "location_name": "Old Location",
        },
        options={
            "name": "New Location",
            CONF_LATITUDE: 52.0,
            CONF_LONGITUDE: 5.0,
        },
        title="Old Location (51.0, 4.0)",
        unique_id="51.0_4.0",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.data[CONF_LATITUDE] == 52.0
    assert entry.data[CONF_LONGITUDE] == 5.0
    assert entry.data["name"] == "New Location"
    assert entry.data["location_id"] == "52.0_5.0"
    assert entry.data["location_name"] == "New Location"
    assert entry.unique_id == "52.0_5.0"
    assert entry.title == "New Location (52.0, 5.0)"


@pytest.mark.asyncio
async def test_setup_entry_prevents_duplicate_coordinates(
    hass: HomeAssistant,
) -> None:
    """Test setup returns False if another entry already polls the target coordinates."""
    entry1 = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "name": "First Entry",
            CONF_LATITUDE: 53.5,
            CONF_LONGITUDE: 6.5,
        },
        unique_id="53.5_6.5",
    )
    entry1.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry1.entry_id)
    await hass.async_block_till_done()

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "name": "Second Entry",
            CONF_LATITUDE: 54.5,
            CONF_LONGITUDE: 7.5,
        },
        options={
            CONF_LATITUDE: 53.5,
            CONF_LONGITUDE: 6.5,
        },
        unique_id="54.5_7.5",
    )
    entry2.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_entity_registry_migration(hass: HomeAssistant) -> None:
    """Test migrating entity unique_id from old format to new format upon setup."""
    from homeassistant.helpers.entity_registry import (
        async_get as async_get_entity_registry,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "name": "Migration Test Location",
            CONF_LATITUDE: 52.0,
            CONF_LONGITUDE: 5.0,
        },
        unique_id="52.0_5.0",
    )
    entry.add_to_hass(hass)

    entity_registry = async_get_entity_registry(hass)
    old_unique_id = f"{entry.entry_id}-melding_migration_test_location"
    old_entity = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=old_unique_id,
        config_entry=entry,
    )
    assert old_entity.unique_id == old_unique_id

    precipitation_entity = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{entry.entry_id}_precipitationrate_total",
        suggested_object_id="totale_neerslag",
        original_name="Totale neerslag",
        config_entry=entry,
    )
    assert precipitation_entity.entity_id == "sensor.totale_neerslag"

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    migrated_entity = entity_registry.async_get(old_entity.entity_id)
    assert migrated_entity is not None
    assert migrated_entity.unique_id == f"{entry.entry_id}_nowcastmessage"

    migrated_precipitation_entity = entity_registry.async_get(
        "sensor.migration_test_location_neerslag_verwacht"
    )
    assert migrated_precipitation_entity is not None
    assert migrated_precipitation_entity.unique_id == (
        f"{entry.entry_id}_precipitationrate_total"
    )


@pytest.mark.asyncio
async def test_entity_registry_migration_preserves_ambiguous_precipitation_id(
    hass: HomeAssistant,
) -> None:
    """Migrate a precipitation entity to legacy_precipitation_entity_id if configured."""
    from homeassistant.helpers.entity_registry import (
        async_get as async_get_entity_registry,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "name": "Migration Test Location",
            CONF_LATITUDE: 52.0,
            CONF_LONGITUDE: 5.0,
        },
        unique_id="52.0_5.0",
    )
    entry.add_to_hass(hass)

    entity_registry = async_get_entity_registry(hass)
    entity = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{entry.entry_id}_precipitationrate_total",
        suggested_object_id="neerslag_verwacht",
        original_name="Custom precipitation name",
        config_entry=entry,
    )

    async_migrate_entity_unique_ids(hass, entry)

    migrated_entity = entity_registry.async_get(
        "sensor.migration_test_location_neerslag_verwacht"
    )
    assert migrated_entity is not None
    assert migrated_entity.unique_id == f"{entry.entry_id}_precipitationrate_total"
