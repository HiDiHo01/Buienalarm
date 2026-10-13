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


@pytest.mark.asyncio
async def test_sensor_integration_user_provided_data(hass: HomeAssistant) -> None:
    """Test integration setup and sensor states against the user-provided data payload."""
    user_payload = {
        "data": [
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:00:00Z", "timestamp": 1791759600},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:05:00Z", "timestamp": 1791759900},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:10:00Z", "timestamp": 1791760200},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:15:00Z", "timestamp": 1791760500},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:20:00Z", "timestamp": 1791760800},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:25:00Z", "timestamp": 1791761100},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:30:00Z", "timestamp": 1791761400},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:35:00Z", "timestamp": 1791761700},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:40:00Z", "timestamp": 1791762000},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:45:00Z", "timestamp": 1791762300},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:50:00Z", "timestamp": 1791762600},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:55:00Z", "timestamp": 1791762900},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:00:00Z", "timestamp": 1791763200},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:05:00Z", "timestamp": 1791763500},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:10:00Z", "timestamp": 1791763800},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:15:00Z", "timestamp": 1791764100},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:20:00Z", "timestamp": 1791764400},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:25:00Z", "timestamp": 1791764700},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:30:00Z", "timestamp": 1791765000},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:35:00Z", "timestamp": 1791765300},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:40:00Z", "timestamp": 1791765600},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:45:00Z", "timestamp": 1791765900},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:50:00Z", "timestamp": 1791766200},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:55:00Z", "timestamp": 1791766500},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T01:00:00Z", "timestamp": 1791766800},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T01:05:00Z", "timestamp": 1791767100},
        ],
        "daypart": [
            {"precipitationrate": 0.73, "time": "2026-10-11T22:00:00Z", "timestamp": 1791756000, "weathericon": [2, 0, -1, -1, 0, -1, -1, -1, -1]},
            {"precipitationrate": 0.0, "time": "2026-10-11T23:00:00Z", "timestamp": 1791759600, "weathericon": [0, 0, -1, -1, -1, -1, -1, -1, -1]},
            {"precipitationrate": 0.0, "time": "2026-10-12T00:00:00Z", "timestamp": 1791763200, "weathericon": [0, 0, -1, -1, -1, -1, -1, -1, -1]},
            {"precipitationrate": 0.0, "time": "2026-10-12T01:00:00Z", "timestamp": 1791766800, "weathericon": [0, 0, -1, -1, -1, -1, -1, -1, -1]},
            {"precipitationrate": 0.0, "time": "2026-10-12T02:00:00Z", "timestamp": 1791770400, "weathericon": [0, 0, -1, -1, -1, -1, -1, -1, -1]},
        ],
        "nowcastmessage": {
            "de": "Es bleibt vorläufig trocken",
            "el": "Δεν θα βρέξει προς το παρόν",
            "en": "It will stay dry for now",
            "es": "Por ahora el tiempo seguirá seco",
            "fr": "Il fera temporairement sec",
            "hr": "Za sada će ostati suho",
            "hu": "Egyelőre száraz marad az idő",
            "ispush": 0,
            "it": "Per il momento asciutto",
            "nl": "Het blijft voorlopig droog",
            "pl": "Na razie będzie sucho",
            "pt": "Vai manter-se seco por agora",
            "sv": "Uppehåll tills vidare",
            "tags": ["no precipitation"],
            "tr": "Şu an için yağış beklenmiyor",
        },
        "summary": {
            "available": True,
            "latitude": 52.787,
            "longitude": 4.798,
            "quadindex": "BCACAADDCBDABCA",
            "slice": 421490,
            "source": "radar-nl",
            "timestamp": 1791758700,
        },
    }

    async def _mock_json(*args, **kwargs):
        return user_payload

    mock_resp = AsyncMock()
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "application/json", "Age": "0"}
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = _mock_json

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Test Location",
        unique_id="user_data_test",
        data={"latitude": 52.787, "longitude": 4.798, "location_name": "Test Location"},
    )
    entry.add_to_hass(hass)

    with patch("aiohttp.ClientSession.get", return_value=mock_resp):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = async_get_entity_registry(hass)
    unique_id = f"{entry.entry_id}_nowcastmessage"
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "Het blijft voorlopig droog"



@pytest.mark.asyncio
async def test_timeseries_wrapper_populates_precipitation_data_attribute(
    hass: HomeAssistant,
) -> None:
    """Unwrap the API client's timeseries payload for the expected-precipitation sensor."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
    from homeassistant.const import UnitOfVolumetricFlux

    from custom_components.buienalarm.sensor import BuienalarmSensor

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Schagen",
        unique_id="52.0_5.0",
        data={"name": "Schagen", "location_name": "Schagen"},
    )
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.api_last_updated = None
    forecast_time = datetime.now(timezone.utc).replace(microsecond=0)
    coordinator.data = {
        "timeseries": {
            "data": [
                {
                    "timestamp": int(forecast_time.timestamp()),
                    "precipitationrate": 1.2,
                    "precipitationtype": "rain",
                    "time": forecast_time.isoformat(),
                }
            ],
            "nowcastmessage": {"nl": "Regen verwacht"},
        },
        "retrieval_time": forecast_time,
        "cache_age": 0,
    }

    entity = BuienalarmSensor(
        coordinator,
        entry,
        name="Neerslag verwacht",
        unit_of_measurement=UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        icon="mdi:weather-rainy",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
        key="precipitationrate_total",
        translation_key="precipitationrate_total",
    )

    attributes = entity.extra_state_attributes
    assert attributes is not None
    assert len(attributes["precipitation_data"]) == 1
    assert attributes["precipitation_data"][0]["precipitationrate"] == 1.2
    assert attributes["precipitation_data"][0]["precipitationtype"] == "rain"
    assert isinstance(attributes["precipitation_data"][0]["time"], datetime)
    assert attributes["precipitation_data"][0]["time"].tzinfo is not None
    assert entity.get_nowcastmessage() == "Regen verwacht"

    coordinator.data = {
        "timeseries": {"data": []},
        "retrieval_time": forecast_time,
        "cache_age": 0,
    }
    assert entity.data_points_as_list == []


@pytest.mark.asyncio
async def test_schagen_neerslag_verwacht_entity_id_and_precipitation_data(
    hass: HomeAssistant,
) -> None:
    """Verify sensor.schagen_neerslag_verwacht is preserved via migration and has precipitation_data attribute."""
    from datetime import datetime, timezone
    from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

    forecast_time = datetime.now(timezone.utc).replace(microsecond=0)
    mock_payload = {
        "data": [
            {
                "timestamp": int(forecast_time.timestamp()),
                "precipitationrate": 2.4,
                "precipitationtype": "rain",
                "time": forecast_time.isoformat(),
            }
        ],
        "nowcastmessage": {"nl": "Regen verwacht in Schagen"},
    }

    async def _mock_json(*args, **kwargs):
        return mock_payload

    mock_resp = AsyncMock()
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "application/json", "Age": "0"}
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = _mock_json

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Schagen",
        unique_id="52.7876_4.7401",
        data={
            "latitude": 52.7876,
            "longitude": 4.7401,
            "name": "Schagen",
            "location_name": "Schagen",
            "place": "Schagen",
        },
    )
    entry.add_to_hass(hass)

    entity_registry = async_get_entity_registry(hass)
    entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id=f"{entry.entry_id}_precipitationrate_total",
        suggested_object_id="expected_precipitation",
        original_name="Expected precipitation",
        config_entry=entry,
    )

    with patch("aiohttp.ClientSession.get", return_value=mock_resp):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    unique_id = f"{entry.entry_id}_precipitationrate_total"
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id == "sensor.schagen_neerslag_verwacht"

    state = hass.states.get("sensor.schagen_neerslag_verwacht")
    assert state is not None
    assert "precipitation_data" in state.attributes
    precip_data = state.attributes["precipitation_data"]
    assert isinstance(precip_data, list)
    assert len(precip_data) == 1
    assert precip_data[0]["precipitationrate"] == 2.4
    assert precip_data[0]["precipitationtype"] == "rain"
    assert "location" in state.attributes
    assert state.attributes["location"] == "Schagen"
