import pytest
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN, SENSORS


@pytest.fixture(autouse=True)
def mock_requests():
    """Prevent real HTTP calls by mocking requests.get with nested 'data' key."""
    with patch("requests.get") as mock_get:
        mock_resp = mock_get.return_value
        inner = [
            {
                "timestamp": 1700000000,
                "precipitationrate": 0.0,
                "precipitationtype": "rain",
                "time": "2023-11-14T10:00:00Z",
            }
        ]
        mock_resp.json.return_value = {
            "data": inner,
            "nowcastmessage": {"nl": "Geen neerslag"},
        }
        yield


@pytest.fixture(autouse=True)
def mock_aiohttp_get():
    """Mock aiohttp.ClientSession.get for Buienalarm."""
    inner = [
        {
            "timestamp": 1700000000,
            "precipitationrate": 0.0,
            "precipitationtype": "rain",
            "time": "2023-11-14T10:00:00Z",
        }
    ]

    async def _mock_json(*args, **kwargs):
        return {
            "data": inner,
            "nowcastmessage": {"nl": "Geen neerslag"},
        }

    mock_resp = AsyncMock()
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "application/json", "Age": "0"}
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = _mock_json

    with patch("aiohttp.ClientSession.get", return_value=mock_resp):
        yield


@pytest.mark.asyncio
async def test_sensor_entities_created_and_populated(
    hass: HomeAssistant,
) -> None:
    """Ensure sensors are created and reflect mocked coordinator data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Test",
        unique_id="test123",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = async_get_entity_registry(hass)

    # Build expected data directly from SENSORS mock
    expected_data = {
        sensor["key"]: (
            3.14 if sensor.get("device_class") or sensor.get("state_class") else "Test message"
        )
        for sensor in SENSORS
    }

    # Verify all sensors exist and have state/attributes
    for sensor in SENSORS:
        unique_id = f"{entry.entry_id}_{sensor['key']}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None, f"Entity for {sensor['key']} not found"

        state = hass.states.get(entity_id)
        assert state is not None, f"State for {entity_id} missing"

    # ---- guard: invalid data structure ----
    bad_resp = AsyncMock()
    bad_resp.__aenter__.return_value = bad_resp
    bad_resp.status = 200
    bad_resp.headers = {"Content-Type": "application/json", "Age": "0"}
    bad_resp.raise_for_status = lambda: None
    bad_resp.json = AsyncMock(return_value=[])

    with patch("aiohttp.ClientSession.get", return_value=bad_resp):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    for sensor in SENSORS:
        unique_id = f"{entry.entry_id}_{sensor['key']}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        state = hass.states.get(entity_id)
        assert state is not None


@pytest.mark.asyncio
async def test_nowcastmessage_edge_cases(hass: HomeAssistant) -> None:
    """Test get_nowcastmessage edge cases such as missing 'nl' key, non-dict payloads, and None coordinator data."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Edge Case Test",
        unique_id="test_nowcast_edge",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "nowcastmessage")

    # 1. Missing 'nl' key in dict
    coordinator.data = {"nowcastmessage": {"en": "No rain"}}
    assert entity.get_nowcastmessage() is None

    # 2. Empty nowcastmessage dict
    coordinator.data = {"nowcastmessage": {}}
    assert entity.get_nowcastmessage() is None

    # 3. Non-mapping nowcastmessage (e.g. string or list)
    coordinator.data = {"nowcastmessage": "invalid_string"}
    assert entity.get_nowcastmessage() is None

    # 4. None nowcastmessage
    coordinator.data = {"nowcastmessage": None}
    assert entity.get_nowcastmessage() is None

    # 5. Coordinator data is None
    coordinator.data = None
    assert entity.get_nowcastmessage() is None

    # 6. Valid nowcastmessage with timestamp substitution
    coordinator.data = {"nowcastmessage": {"nl": "Regen om {1700000000}"}}
    result = entity.get_nowcastmessage()
    assert result is not None
    assert "Regen om" in result

    # 7. Valid nowcastmessage without placeholders
    coordinator.data = {"nowcastmessage": {"nl": "Geen neerslag"}}
    assert entity.get_nowcastmessage() == "Geen neerslag"


@pytest.mark.asyncio
async def test_buienalarm_entity_untrusted_data_handling(hass: HomeAssistant) -> None:
    """Test BuienalarmEntity methods with untrusted, None, or malformed coordinator data."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Untrusted Data Test",
        unique_id="test_untrusted_data",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "test_sensor")

    invalid_data_samples = [
        None,
        {},
        "invalid string data",
        [1, 2, 3],
        {"data": "not a list"},
        {"data": None},
    ]

    for sample in invalid_data_samples:
        coordinator.data = sample

        assert entity.get_mycastmessage() == "Geen data"
        assert entity.get_precipitation_duration() == 0
        assert entity.get_total_precipitation_rate() == 0.0
        assert entity.get_total_precipitation_rate_for_next_hour() == 0.0
        assert entity.get_current_precipitation() == 0.0
        assert entity.get_current_precipitation_rate_desc() == "Geen neerslag"
        assert entity.get_current_precipitation_type() == "Geen neerslag"
        assert entity.get_next_precipitation() is None
        assert entity.check_rain_data_validity() is False
        assert entity.get_precipitation_periods_as_dict() == []
        assert entity._get_precipitation_periods() == []
        assert entity.data_points_as_list == []
        assert entity.get_data("non_existent_key") is None


@pytest.mark.asyncio
async def test_buienalarm_entity_invalid_precipitation_rates(hass: HomeAssistant) -> None:
    """Test BuienalarmEntity calculations with nonnumeric/invalid precipitationrate and timestamp fields."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Invalid Rates Test",
        unique_id="test_invalid_rates",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "test_sensor")

    now_ts = int(datetime.now(timezone.utc).timestamp())

    coordinator.data = {
        "data": [
            {"timestamp": now_ts + 60, "precipitationrate": "invalid_string", "precipitationtype": "rain"},
            {"timestamp": now_ts + 120, "precipitationrate": None, "precipitationtype": "rain"},
            {"timestamp": "bad_timestamp", "precipitationrate": 2.5, "precipitationtype": "rain"},
            {"timestamp": now_ts + 180, "precipitationrate": "1.5", "precipitationtype": "rain"},
            {"timestamp": now_ts + 240, "precipitationrate": 0.5, "precipitationtype": "rain"},
        ]
    }

    assert entity.get_total_precipitation_rate_for_next_hour() >= 0.0
    assert entity.get_total_precipitation_rate() >= 0.0
    assert entity.get_precipitation_duration() >= 0
    assert entity.get_mycastmessage() != "Geen data"
    assert entity.get_current_precipitation_rate_desc() in ("Geen neerslag", "Lichte regen", "Motregen")
    assert entity.get_current_precipitation_type() in ("Geen neerslag", "Regen")

    # Ensure payload where the last item is malformed/non-dict does not break get_mycastmessage()
    coordinator.data = {
        "data": [
            {"timestamp": now_ts + 60, "precipitationrate": 2.0, "precipitationtype": "rain"},
            {"timestamp": now_ts + 120, "precipitationrate": 1.0, "precipitationtype": "rain"},
            "invalid_final_item_not_dict",
        ]
    }
    msg = entity.get_mycastmessage()
    assert msg is not None
    assert msg != "Geen data"


@pytest.mark.asyncio
async def test_buienalarm_sensor_entity_availability(hass: HomeAssistant) -> None:
    """Test BuienalarmSensorEntity available property returns False when coordinator data is empty."""
    from unittest.mock import MagicMock
    from homeassistant.components.sensor import SensorEntityDescription
    from custom_components.buienalarm.entity import BuienalarmSensorEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Availability Test",
        unique_id="test_availability",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    coordinator.last_update_success = True
    desc = SensorEntityDescription(key="nowcastmessage", name="Test Sensor")
    sensor_entity = BuienalarmSensorEntity(coordinator, entry, desc, "loc_123", "Test Location")

    # When coordinator data is valid dict
    coordinator.data = {"nowcastmessage": "Rain expected"}
    assert sensor_entity.available is True

    # When coordinator data is empty dict
    coordinator.data = {}
    assert sensor_entity.available is False

    # When coordinator data is None or non-mapping
    coordinator.data = None
    assert sensor_entity.available is False

    # When last_update_success is False
    coordinator.last_update_success = False
    coordinator.data = {"nowcastmessage": "Rain expected"}
    assert sensor_entity.available is False


@pytest.mark.asyncio
async def test_buienalarm_entity_missing_or_none_precipitationtype(
    hass: HomeAssistant,
) -> None:
    """Test get_current_precipitation and get_current_precipitation_type when precipitationtype is None or missing."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Missing Precip Type Test",
        unique_id="test_missing_precip_type",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "precipitationrate_now")

    now_ts = int(datetime.now(timezone.utc).timestamp())

    # 1. precipitationtype is explicitly None
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": 2.5,
                "precipitationtype": None,
            }
        ]
    }

    assert entity.get_current_precipitation() == 2.5
    assert entity.get_current_precipitation_type() == "Onbekend"

    # 2. precipitationtype key is omitted
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": 1.8,
            }
        ]
    }

    assert entity.get_current_precipitation() == 1.8
    assert entity.get_current_precipitation_type() == "Onbekend"

    # 3. precipitationtype is unknown string
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": 0.5,
                "precipitationtype": "hail",
            }
        ]
    }

    assert entity.get_current_precipitation() == 0.5
    assert entity.get_current_precipitation_type() == "Onbekend"
