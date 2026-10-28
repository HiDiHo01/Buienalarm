import pytest
from copy import deepcopy
from datetime import datetime, timedelta, timezone, tzinfo
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN, SENSORS
from custom_components.buienalarm.sensor_types import SENSOR_DESCRIPTIONS


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
            3.14
            if sensor.get("device_class") or sensor.get("state_class")
            else "Test message"
        )
        for sensor in SENSORS
    }

    # Verify all sensors exist and have state/attributes
    for sensor in SENSORS:
        unique_id = f"{entry.entry_id}_{sensor['key']}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None, f"Entity for {sensor['key']} not found"

        state = hass.states.get(entity_id)
        if sensor.get("enabled_by_default", True):
            assert state is not None, f"State for {entity_id} missing"
            if sensor["key"] == "precipitationrate_now":
                assert state.state == "unavailable"
        else:
            assert state is None

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
        if sensor.get("enabled_by_default", True):
            assert state is not None
        else:
            assert state is None


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

    await hass.config.async_set_time_zone("Europe/Amsterdam")

    # 6. Valid nowcastmessage with timestamp substitution
    coordinator.data = {"nowcastmessage": {"nl": "Regen om {1700000000}"}}
    result = entity.get_nowcastmessage()
    assert result == "Regen om 23:13"

    # 7. Valid nowcastmessage without placeholders
    coordinator.data = {"nowcastmessage": {"nl": "Geen neerslag"}}
    assert entity.get_nowcastmessage() == "Geen neerslag"

    # 8. Out-of-bounds timestamp placeholder in nowcastmessage
    coordinator.data = {"nowcastmessage": {"nl": "Regen om {99999999999999999999}"}}
    assert entity.get_nowcastmessage() == "Regen om {99999999999999999999}"


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
        assert entity.get_total_precipitation_rate() is None
        assert entity.get_total_precipitation_rate_for_next_hour() is None
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
async def test_buienalarm_entity_invalid_precipitation_rates(
    hass: HomeAssistant,
) -> None:
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
            {
                "timestamp": now_ts + 60,
                "precipitationrate": "invalid_string",
                "precipitationtype": "rain",
            },
            {
                "timestamp": now_ts + 120,
                "precipitationrate": None,
                "precipitationtype": "rain",
            },
            {
                "timestamp": "bad_timestamp",
                "precipitationrate": 2.5,
                "precipitationtype": "rain",
            },
            {
                "timestamp": now_ts + 180,
                "precipitationrate": "1.5",
                "precipitationtype": "rain",
            },
            {
                "timestamp": now_ts + 240,
                "precipitationrate": 0.5,
                "precipitationtype": "rain",
            },
        ]
    }

    assert entity.get_total_precipitation_rate_for_next_hour() is None
    assert entity.get_total_precipitation_rate() is None
    assert entity.get_precipitation_duration() >= 0
    assert entity.get_mycastmessage() != "Geen data"
    assert entity.get_current_precipitation_rate_desc() in (
        "Geen neerslag",
        "Lichte regen",
        "Motregen",
    )
    assert entity.get_current_precipitation_type() in ("Geen neerslag", "Regen")

    # Ensure payload where the last item is malformed/non-dict does not break get_mycastmessage()
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts + 60,
                "precipitationrate": 2.0,
                "precipitationtype": "rain",
            },
            {
                "timestamp": now_ts + 120,
                "precipitationrate": 1.0,
                "precipitationtype": "rain",
            },
            "invalid_final_item_not_dict",
        ]
    }
    msg = entity.get_mycastmessage()
    assert msg is not None
    assert msg != "Geen data"


@pytest.mark.asyncio
async def test_buienalarm_sensor_availability(hass: HomeAssistant) -> None:
    """Test BuienalarmSensor available property returns False when required key-specific payload fields are missing or invalid."""
    from collections import UserDict
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Availability Test",
        unique_id="test_availability",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    coordinator.last_update_success = True
    nowcast_sensor = BuienalarmSensor(
        coordinator,
        entry,
        name="Nowcast message",
        unit_of_measurement=None,
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=None,
        key="nowcastmessage",
    )
    rate_sensor = BuienalarmSensor(
        coordinator,
        entry,
        name="Current Precipitation Rate",
        unit_of_measurement="mm/h",
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=None,
        key="precipitationrate_now",
    )

    # When payload contains both nowcastmessage and data
    coordinator.data = {"nowcastmessage": {"nl": "Regen verwacht"}, "data": []}
    assert nowcast_sensor.available is True
    assert rate_sensor.available is False

    # When payload contains only nowcastmessage (data missing or invalid)
    coordinator.data = {"nowcastmessage": {"nl": "Regen verwacht"}}
    assert nowcast_sensor.available is True
    assert rate_sensor.available is False

    # When payload contains only data (nowcastmessage missing or invalid)
    coordinator.data = {"data": []}
    assert nowcast_sensor.available is False
    assert rate_sensor.available is False

    # When coordinator data is a custom Mapping (UserDict)
    coordinator.data = UserDict(
        {"nowcastmessage": {"nl": "Regen verwacht"}, "data": []}
    )
    assert nowcast_sensor.available is True
    assert rate_sensor.available is False

    # When coordinator data wraps timeseries with valid payload
    coordinator.data = {
        "timeseries": {"nowcastmessage": {"nl": "Regen verwacht"}, "data": []}
    }
    assert nowcast_sensor.available is True
    assert rate_sensor.available is False

    # A wrapped payload with a valid current reading is available.
    coordinator.data = UserDict(
        {
            "timeseries": UserDict(
                {
                    "nowcastmessage": {"nl": "Regen verwacht"},
                    "data": [
                        UserDict(
                            {
                                "timestamp": datetime.now(timezone.utc).timestamp(),
                                "precipitationrate": 2.5,
                                "precipitationtype": "rain",
                            }
                        )
                    ],
                }
            )
        }
    )
    assert nowcast_sensor.available is True
    assert rate_sensor.available is True
    assert rate_sensor.native_value == pytest.approx(2.5)

    # When payload is missing required forecast fields
    coordinator.data = {"unrelated_field": "some_value"}
    assert nowcast_sensor.available is False
    assert rate_sensor.available is False

    coordinator.data = {"data": "not_a_list"}
    assert rate_sensor.available is False

    coordinator.data = {"nowcastmessage": "not_a_mapping"}
    assert nowcast_sensor.available is False

    # When coordinator data wraps timeseries but timeseries is empty dict or None
    coordinator.data = {"timeseries": {}}
    assert nowcast_sensor.available is False
    assert rate_sensor.available is False

    coordinator.data = {"timeseries": None}
    assert nowcast_sensor.available is False
    assert rate_sensor.available is False

    coordinator.data = {"timeseries": "not_a_dict"}
    assert nowcast_sensor.available is False
    assert rate_sensor.available is False

    # When coordinator data is empty dict
    coordinator.data = {}
    assert nowcast_sensor.available is False
    assert rate_sensor.available is False

    # When coordinator data is None or non-mapping
    coordinator.data = None
    assert nowcast_sensor.available is False
    assert rate_sensor.available is False

    # When last_update_success is False
    coordinator.last_update_success = False
    coordinator.data = {"nowcastmessage": {"nl": "Regen verwacht"}, "data": []}
    assert nowcast_sensor.available is False
    assert rate_sensor.available is False


@pytest.mark.asyncio
@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize(
    ("message", "expected_available"),
    [
        (None, False),
        ([], False),
        ("Geen neerslag", False),
        ({}, False),
        ({"en": "No rain"}, False),
        ({"nl": None}, False),
        ({"nl": ""}, False),
        ({"nl": 1}, False),
        ({"nl": False}, False),
        ({"nl": "Geen neerslag"}, True),
        ({"nl": "Regen om {1700000000}"}, True),
    ],
)
async def test_nowcast_availability_requires_dutch_message(
    hass: HomeAssistant,
    wrapped: bool,
    message: object,
    expected_available: bool,
) -> None:
    """Message availability agrees with the getter even without forecast data."""
    from collections import UserDict
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    coordinator = MagicMock()
    coordinator.last_update_success = True
    payload = UserDict(
        {"nowcastmessage": UserDict(message) if isinstance(message, dict) else message}
    )
    coordinator.data = UserDict({"timeseries": payload}) if wrapped else payload
    sensor = BuienalarmSensor(
        coordinator,
        MockConfigEntry(domain=DOMAIN, data={}),
        name="Nowcast message",
        unit_of_measurement=None,
        icon=None,
        device_class=None,
        state_class=None,
        key="nowcastmessage",
    )

    assert sensor.available is expected_available
    assert (sensor.native_value is not None) is expected_available
    coordinator.last_update_success = False
    assert sensor.available is False
    coordinator.last_update_success = True
    assert sensor.available is expected_available


@pytest.mark.asyncio
@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize(
    "key", ["precipitationrate_total", "precipitationrate_hour", "mycastmessage"]
)
@pytest.mark.parametrize(
    ("forecast", "expected_available"),
    [
        (None, False),
        ({}, False),
        ("invalid", False),
        ([], False),
        ([None, "invalid", {}], False),
        ([{"timestamp": 1700000000}], False),
        ([{"precipitationrate": 1.0}], False),
        ([{"timestamp": True, "precipitationrate": 1.0}], False),
        ([{"timestamp": "invalid", "precipitationrate": 1.0}], False),
        ([{"timestamp": float("nan"), "precipitationrate": 1.0}], False),
        ([{"timestamp": float("inf"), "precipitationrate": 1.0}], False),
        ([{"timestamp": 10**400, "precipitationrate": 1.0}], False),
        ([{"timestamp": 253402300800, "precipitationrate": 1.0}], False),
        ([{"timestamp": -1, "precipitationrate": 1.0}], False),
        ([{"timestamp": 1700000000, "precipitationrate": None}], False),
        ([{"timestamp": 1700000000, "precipitationrate": True}], False),
        ([{"timestamp": 1700000000, "precipitationrate": "invalid"}], False),
        ([{"timestamp": 1700000000, "precipitationrate": "2,5"}], False),
        ([{"timestamp": 1700000000, "precipitationrate": float("nan")}], False),
        ([{"timestamp": 1700000000, "precipitationrate": float("inf")}], False),
        ([{"timestamp": 1700000000, "precipitationrate": 10**400}], False),
        ([{"timestamp": 1700000000, "precipitationrate": -1.0}], False),
        ([{"timestamp": 1699999700, "precipitationrate": 1.0}], False),
        ([{"timestamp": 1699999701, "precipitationrate": 1.0}], True),
        ([{"timestamp": 1700000000, "precipitationrate": 0.0}], True),
        ([{"timestamp": 1700000000, "precipitationrate": 2.5}], True),
        ([{"timestamp": 1700000300, "precipitationrate": "2.5"}], True),
        ([None, {}, {"timestamp": 1700000300, "precipitationrate": 0.0}], True),
    ],
)
async def test_forecast_sensor_availability_requires_usable_data(
    hass: HomeAssistant,
    freezer,
    wrapped: bool,
    key: str,
    forecast: object,
    expected_available: bool,
) -> None:
    """Missing, invalid, or expired forecasts cannot establish a dry state."""
    from collections import UserDict
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    freezer.move_to(datetime.fromtimestamp(1700000000, timezone.utc))
    coordinator = MagicMock()
    coordinator.last_update_success = True
    payload = UserDict({"data": forecast})
    coordinator.data = UserDict({"timeseries": payload}) if wrapped else payload
    sensor = BuienalarmSensor(
        coordinator,
        MockConfigEntry(domain=DOMAIN, data={}),
        name=key,
        unit_of_measurement=None,
        icon=None,
        device_class=None,
        state_class=None,
        key=key,
    )

    assert sensor.available is expected_available
    if expected_available:
        assert sensor.native_value is not None
    coordinator.last_update_success = False
    assert sensor.available is False
    coordinator.last_update_success = True
    assert sensor.available is expected_available


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("timestamp", "hour", "total", "message"),
    [
        (1699999700, False, False, False),
        (1699999701, True, True, True),
        (1700003599, True, True, True),
        (1700003600, False, True, True),
        (1700003601, False, True, True),
        (1700007199, False, True, True),
        (1700007200, False, False, True),
        (1700007201, False, False, True),
        ("1700000300", True, True, True),
        ("1700003600", False, True, True),
        ("1700007200", False, False, True),
    ],
)
async def test_forecast_availability_matches_calculation_window(
    hass: HomeAssistant,
    freezer,
    timestamp: object,
    hour: bool,
    total: bool,
    message: bool,
) -> None:
    """Only readings accepted within each calculation's window establish data."""
    from collections import UserDict
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    freezer.move_to(datetime.fromtimestamp(1700000000, timezone.utc))
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "data": [UserDict({"timestamp": timestamp, "precipitationrate": 2.5})]
    }
    for key, expected_available in (
        ("precipitationrate_hour", hour),
        ("precipitationrate_total", total),
        ("mycastmessage", message),
    ):
        sensor = BuienalarmSensor(
            coordinator,
            MockConfigEntry(domain=DOMAIN, data={}),
            name=key,
            unit_of_measurement=None,
            icon=None,
            device_class=None,
            state_class=None,
            key=key,
        )
        assert sensor.available is expected_available
        if key != "mycastmessage":
            assert (sensor.native_value is not None) is expected_available


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("timestamp", "rate", "expected_available"),
    [
        pytest.param(1700000000, 2.5, True, id="current-rain"),
        pytest.param(1700000000, 0.0, True, id="current-dry"),
        pytest.param("1700000000", "2,5", True, id="numeric-strings"),
        pytest.param(1699999701, 2.5, True, id="inside-bin"),
        pytest.param(1699999700, 2.5, False, id="bin-end-exclusive"),
        pytest.param(1699999400, 2.5, False, id="stale"),
        pytest.param(1700000001, 2.5, False, id="future"),
        pytest.param(None, 2.5, False, id="missing-timestamp"),
        pytest.param(True, 2.5, False, id="boolean-timestamp"),
        pytest.param("invalid", 2.5, False, id="malformed-timestamp"),
        pytest.param(float("nan"), 2.5, False, id="nan-timestamp"),
        pytest.param(float("inf"), 2.5, False, id="infinite-timestamp"),
        pytest.param(10**400, 2.5, False, id="overflow-timestamp"),
        pytest.param(1700000000, None, False, id="missing-rate"),
        pytest.param(1700000000, True, False, id="boolean-rate"),
        pytest.param(1700000000, -1.0, False, id="negative-rate"),
        pytest.param(1700000000, "invalid", False, id="malformed-rate"),
        pytest.param(1700000000, float("nan"), False, id="nan-rate"),
        pytest.param(1700000000, float("inf"), False, id="infinite-rate"),
        pytest.param(1700000000, 10**400, False, id="overflow-rate"),
    ],
)
async def test_current_rate_availability_requires_valid_active_reading(
    hass: HomeAssistant,
    freezer,
    timestamp: object,
    rate: object,
    expected_available: bool,
) -> None:
    """Only expose a rate when a valid reading covers the current five-minute bin."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    freezer.move_to(datetime.fromtimestamp(1700000000, timezone.utc))
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "data": [None, {}, {"timestamp": timestamp, "precipitationrate": rate}]
    }
    sensor = BuienalarmSensor(
        coordinator,
        MockConfigEntry(domain=DOMAIN, data={}),
        name="Current Precipitation Rate",
        unit_of_measurement="mm/h",
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=None,
        key="precipitationrate_now",
    )

    assert sensor.available is expected_available
    if expected_available:
        expected_rate = float(rate.replace(",", ".")) if isinstance(rate, str) else rate
        assert sensor.native_value == pytest.approx(expected_rate)


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
@pytest.mark.parametrize(
    "precipitation_type", [None, "rain", "snow"], ids=["dry", "rain", "snow"]
)
async def test_sensor_integration_user_provided_data(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    user_sample_payload: dict[str, object],
    precipitation_type: str | None,
) -> None:
    """Verify all entity states for the sample forecast and positive rain/snow variants."""
    freezer.move_to("2026-10-11T23:00:00Z")
    await hass.config.async_set_time_zone("UTC")
    response_payload = deepcopy(user_sample_payload)
    if precipitation_type is not None:
        forecast_points = response_payload["data"]
        assert isinstance(forecast_points, list)
        # Three wet five-minute bins, then dry: 15 minutes at 2.4 mm/h.
        for forecast_point in forecast_points[:3]:
            assert isinstance(forecast_point, dict)
            forecast_point["precipitationrate"] = 2.4
            forecast_point["precipitationtype"] = precipitation_type
        nowcast_message = response_payload["nowcastmessage"]
        assert isinstance(nowcast_message, dict)
        nowcast_message["nl"] = "Neerslag verwacht"

    async def _mock_json(*_args: object, **_kwargs: object) -> dict[str, object]:
        """Return the selected forecast through the mocked HTTP response."""
        return response_payload

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
    # Exercise the optional period sensor as a user-enabled entity.
    entity_registry = async_get_entity_registry(hass)
    entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{entry.entry_id}_precipitation_periods",
        config_entry=entry,
        suggested_object_id="test_precipitation_periods",
    )

    with patch("aiohttp.ClientSession.get", return_value=mock_resp):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = async_get_entity_registry(hass)

    expected_sensor_states = {
        "nowcastmessage": "Het blijft voorlopig droog",
        "mycastmessage": "Geen neerslag",
        "precipitationrate_now_desc": "Geen neerslag",
        "precipitationtype_now": "Geen neerslag",
        "next_precipitation": STATE_UNKNOWN,
        "precipitation_duration": "0",
        "precipitationrate_now": "0.0",
        "precipitationrate_hour": "0.0",
        "precipitationrate_total": "0.0",
        "precipitation_periods": "0",
    }
    if precipitation_type is not None:
        expected_description, expected_type = {
            "rain": ("Matige regen", "Regen"),
            "snow": ("Matige sneeuw", "Sneeuw"),
        }[precipitation_type]
        expected_sensor_states.update(
            {
                "nowcastmessage": "Neerslag verwacht",
                "mycastmessage": "Neerslag duurt nog 15 minuten en stopt rond 23:15",
                "precipitationrate_now_desc": expected_description,
                "precipitationtype_now": expected_type,
                "next_precipitation": "0",
                "precipitation_duration": "15",
                "precipitationrate_now": "2.4",
                "precipitationrate_hour": "0.6",
                "precipitationrate_total": "0.3",
                "precipitation_periods": "1",
            }
        )

    for key, expected_state in expected_sensor_states.items():
        unique_id = f"{entry.entry_id}_{key}"
        entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        assert entity_id is not None, f"Entity for sensor {key} not found"
        state = hass.states.get(entity_id)
        assert state is not None, f"State for sensor {key} missing"
        assert state.state == expected_state, f"Sensor {key} state mismatch"
        if key == "precipitation_duration":
            assert state.attributes.get("state_class") is None

    expected_binary_sensor_states = {
        "precipitation_expected": "off",
        "currently_raining": "off",
        "currently_snowing": "off",
    }
    if precipitation_type is not None:
        expected_binary_sensor_states.update(
            {
                "precipitation_expected": "on",
                "currently_raining": "on" if precipitation_type == "rain" else "off",
                "currently_snowing": "on" if precipitation_type == "snow" else "off",
            }
        )

    for key, expected_state in expected_binary_sensor_states.items():
        unique_id = f"{entry.entry_id}_{key}"
        entity_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, unique_id
        )
        assert entity_id is not None, f"Entity for binary sensor {key} not found"
        state = hass.states.get(entity_id)
        assert state is not None, f"State for binary sensor {key} missing"
        assert state.state == expected_state, f"Binary sensor {key} state mismatch"


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
    from homeassistant.helpers.entity_registry import (
        async_get as async_get_entity_registry,
    )

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


@pytest.mark.asyncio
async def test_active_5min_bin_included_in_periods_duration_totals(
    hass: HomeAssistant,
) -> None:
    """Verify that an active 5-minute forecast bin (started 2 min ago) is included in calculations."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Active Bin Test",
        unique_id="test_active_bin",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "precipitation_periods")

    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()
    active_bin_ts = now_ts - 120  # Bin started 2 min ago, ends in 3 min

    coordinator.data = {
        "data": [
            {
                "timestamp": active_bin_ts,
                "precipitationrate": 3.0,
                "precipitationtype": "rain",
            },
            {
                "timestamp": active_bin_ts + 300,
                "precipitationrate": 1.0,
                "precipitationtype": "rain",
            },
            {
                "timestamp": active_bin_ts + 600,
                "precipitationrate": 0.0,
                "precipitationtype": "rain",
            },
        ]
    }

    periods = entity._get_precipitation_periods()
    assert len(periods) == 1
    assert periods[0]["duration_minutes"] == 10
    assert periods[0]["precipitationrate"] == 2.0

    duration = entity.get_precipitation_duration()
    assert duration == 10

    (
        rain_start,
        rain_stop,
        rain_restart,
        rain_dur,
        rain_stopped,
    ) = entity.get_rain_start_time_and_duration(coordinator.data["data"])
    assert rain_dur == 10
    assert rain_stopped is True

    rate = entity.calculate_total_precipitation_rate(
        coordinator.data["data"], now, now + timedelta(hours=1)
    )
    assert rate > 0.0


@pytest.mark.asyncio
async def test_buienalarm_entity_malformed_non_mapping_list_items(
    hass: HomeAssistant,
) -> None:
    """Verify BuienalarmEntity handles non-mapping items and items with raising/non-callable .get in data list safely."""
    from collections import UserDict
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    class RaisingGetItem:
        """Object with a get attribute that raises an exception when called."""

        def get(self, *args, **kwargs):
            raise RuntimeError("Corrupted get call")

    class NonCallableGetItem:
        """Object with a get attribute that is not callable."""

        get = "not_a_method"

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Non-Mapping Items Test",
        unique_id="test_non_mapping_items",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "custom_key")

    now_ts = int(datetime.now(timezone.utc).timestamp())

    # Test raw scalar fallback in get_data with non-dict Mapping (UserDict)
    coordinator.data = UserDict(
        {
            "custom_key": "custom_value",
            "data": [
                "invalid_string_item\nwith_newline",
                12345,
                None,
                [1, 2, 3],
                RaisingGetItem(),
                NonCallableGetItem(),
                {
                    "timestamp": now_ts + 300,
                    "precipitationrate": 2.5,
                    "precipitationtype": "rain",
                },
                "another_invalid_item",
            ],
        }
    )

    assert entity.get_data("custom_key") == "custom_value"
    assert entity.get_current_precipitation_rate_desc() == "Geen neerslag"
    assert entity.get_current_precipitation_type() == "Geen neerslag"
    assert entity.get_precipitation_duration() >= 0
    assert entity.get_next_precipitation() == 5


@pytest.mark.asyncio
async def test_data_points_as_list_skips_entries_without_valid_time_sources(
    hass: HomeAssistant,
) -> None:
    """Verify data_points_as_list skips entries where neither timestamp nor time yields a valid datetime."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Data Points Time Test",
        unique_id="test_time_sources",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "precipitationrate_total")

    coordinator.data = {
        "data": [
            # 1. Missing both timestamp and time -> skipped
            {"precipitationrate": 1.0, "precipitationtype": "rain"},
            # 2. Invalid timestamp and invalid time -> skipped
            {"timestamp": "bad", "time": "invalid_iso", "precipitationrate": 1.0},
            # 3. Only numeric timestamp present -> kept
            {
                "timestamp": 1700000000,
                "precipitationrate": 2.0,
                "precipitationtype": "rain",
            },
            # 4. Only valid ISO time present -> kept
            {
                "time": "2023-11-14T12:00:00Z",
                "precipitationrate": 0.5,
                "precipitationtype": "rain",
            },
        ]
    }

    points = entity.data_points_as_list
    assert len(points) == 2
    assert points[0]["precipitationrate"] == 2.0
    assert points[0]["timestamp"] == 1700000000
    assert points[1]["precipitationrate"] == 0.5
    assert points[1]["timestamp"] == int(
        datetime.fromisoformat("2023-11-14T12:00:00Z").timestamp()
    )


@pytest.mark.asyncio
async def test_boolean_timestamps_and_rates_rejected(hass: HomeAssistant) -> None:
    """Verify boolean values in timestamp or precipitationrate fields are safely rejected."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Boolean Rejection Test",
        unique_id="test_bool_rejection",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "precipitation_duration")

    now_ts = datetime.now(timezone.utc).timestamp()

    coordinator.data = {
        "data": [
            {
                "timestamp": True,
                "precipitationrate": 2.5,
            },
            {
                "timestamp": now_ts + 300,
                "precipitationrate": True,
            },
            {
                "timestamp": False,
                "precipitationrate": False,
            },
        ]
    }

    assert entity._get_precipitation_periods() == []
    assert entity.get_precipitation_duration() == 0
    assert entity.get_total_precipitation_rate_for_next_hour() is None

    # Verify current precipitation, rate desc, precip type, and next precip reject booleans
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": True,
                "precipitationtype": "rain",
            },
            {
                "timestamp": now_ts + 300,
                "precipitationrate": True,
                "precipitationtype": "rain",
            },
        ]
    }

    assert entity.get_current_precipitation() == 0.0
    assert entity.get_current_precipitation_rate_desc() == "Geen neerslag"
    assert entity.get_current_precipitation_type() == "Geen neerslag"
    assert entity.get_next_precipitation() is None

    # Verify non-finite and overflowing values (NaN, Inf, OverflowError, 1e300) are rejected
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": float("nan"),
                "precipitationtype": "rain",
            },
            {
                "timestamp": float("inf"),
                "precipitationrate": float("inf"),
                "precipitationtype": "rain",
            },
            {
                "timestamp": 1e300,
                "precipitationrate": 2.5,
                "precipitationtype": "rain",
            },
            {
                "timestamp": now_ts + 300,
                "precipitationrate": "1e1000000",
                "precipitationtype": "rain",
            },
        ]
    }

    assert entity.get_current_precipitation() == 0.0
    assert entity.get_current_precipitation_rate_desc() == "Geen neerslag"
    assert entity.get_current_precipitation_type() == "Geen neerslag"
    assert entity.get_next_precipitation() is None
    assert entity.get_precipitation_duration() == 0
    assert entity.get_rain_start_time_and_duration(coordinator.data["data"]) is None

    # Verify boolean timestamps are rejected
    coordinator.data = {
        "data": [
            {
                "timestamp": True,
                "precipitationrate": 2.5,
                "precipitationtype": "rain",
            }
        ]
    }

    assert entity.get_current_precipitation() == 0.0
    assert entity.get_current_precipitation_rate_desc() == "Geen neerslag"
    assert entity.get_current_precipitation_type() == "Geen neerslag"
    assert entity.get_next_precipitation() is None


@pytest.mark.asyncio
async def test_dynamic_sensor_icons(hass: HomeAssistant) -> None:
    """Test dynamic icon computation for precipitation rate and precipitation type sensors."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Dynamic Icon Test",
        unique_id="test_dynamic_icons",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    coordinator.last_update_success = True

    now_ts = int(datetime.now(timezone.utc).timestamp())

    # Create sensor instances
    precip_rate_sensor = BuienalarmSensor(
        coordinator,
        entry,
        name="Current precipitation",
        unit_of_measurement="mm/h",
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=None,
        key="precipitationrate_now",
    )

    precip_rate_hour_sensor = BuienalarmSensor(
        coordinator,
        entry,
        name="Hourly Precipitation Rate",
        unit_of_measurement="mm/h",
        icon="mdi:weather-pouring",
        device_class=None,
        state_class=None,
        key="precipitationrate_hour",
    )

    precip_rate_total_sensor = BuienalarmSensor(
        coordinator,
        entry,
        name="Total Precipitation Rate",
        unit_of_measurement="mm/h",
        icon="mdi:weather-pouring",
        device_class=None,
        state_class=None,
        key="precipitationrate_total",
    )

    precip_type_sensor = BuienalarmSensor(
        coordinator,
        entry,
        name="Current precipitation type",
        unit_of_measurement=None,
        icon="mdi:weather-partly-rainy",
        device_class=None,
        state_class=None,
        key="precipitationtype_now",
    )

    precip_desc_sensor = BuienalarmSensor(
        coordinator,
        entry,
        name="Precipitation Description",
        unit_of_measurement=None,
        icon="mdi:weather-cloudy-alert",
        device_class=None,
        state_class=None,
        key="precipitationrate_now_desc",
    )

    # 1. Test when dry (rate = 0.0, type = "Geen neerslag")
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": 0.0,
                "precipitationtype": "none",
            }
        ]
    }

    assert precip_rate_sensor.icon == "mdi:weather-sunny"
    assert precip_rate_hour_sensor.icon == "mdi:weather-sunny"
    assert precip_rate_total_sensor.icon == "mdi:weather-sunny"
    assert precip_type_sensor.icon == "mdi:weather-sunny"
    assert precip_desc_sensor.icon == "mdi:weather-sunny"

    # 2. Test when raining (rate = 2.5, type = "rain")
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": 2.5,
                "precipitationtype": "rain",
            }
        ]
    }

    assert precip_rate_sensor.icon == "mdi:weather-pouring"
    assert precip_rate_hour_sensor.icon == "mdi:weather-pouring"
    assert precip_rate_total_sensor.icon == "mdi:weather-pouring"
    assert precip_type_sensor.icon == "mdi:weather-pouring"
    assert precip_desc_sensor.icon == "mdi:weather-pouring"

    # 3. Test when snowing (type = "snow")
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": 1.0,
                "precipitationtype": "snow",
            }
        ]
    }

    assert precip_type_sensor.icon == "mdi:weather-snowy"
    assert precip_desc_sensor.icon == "mdi:weather-snowy"


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["precipitationtype_now", "precipitationrate_now_desc"])
@pytest.mark.parametrize("wrapped", [False, True], ids=["unwrapped", "wrapped"])
@pytest.mark.parametrize(
    "forecast",
    [
        pytest.param([], id="empty"),
        pytest.param(None, id="null"),
        pytest.param({}, id="not-a-list"),
        pytest.param([None], id="invalid-point"),
        pytest.param([{"precipitationrate": 0.0}], id="missing-timestamp"),
        pytest.param(
            [{"timestamp": "invalid", "precipitationrate": 0.0}],
            id="malformed-timestamp",
        ),
        pytest.param([{"timestamp": 1700000000}], id="missing-rate"),
        pytest.param(
            [{"timestamp": 1700000000, "precipitationrate": "invalid"}],
            id="malformed-rate",
        ),
        pytest.param(
            [{"timestamp": 1700000000, "precipitationrate": True}],
            id="boolean-rate",
        ),
        pytest.param(
            [{"timestamp": 1700000000, "precipitationrate": float("nan")}],
            id="non-finite-rate",
        ),
        pytest.param(
            [{"timestamp": 1700000000, "precipitationrate": -1.0}],
            id="negative-rate",
        ),
        pytest.param([{"timestamp": 1699999699, "precipitationrate": 0.0}], id="stale"),
        pytest.param(
            [{"timestamp": 1699999700, "precipitationrate": 0.0}], id="expired-bin"
        ),
        pytest.param(
            [{"timestamp": 1700000001, "precipitationrate": 0.0}], id="future-bin"
        ),
    ],
)
async def test_current_precipitation_icons_require_valid_current_interval(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    key: str,
    wrapped: bool,
    forecast: object,
) -> None:
    """Unknown current conditions retain the configured icon instead of sunny."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    freezer.move_to("2023-11-14T22:13:20Z")  # 1700000000
    payload = {"data": forecast}
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"timeseries": payload} if wrapped else payload
    sensor = BuienalarmSensor(
        coordinator,
        MockConfigEntry(domain=DOMAIN, data={}),
        name="Current precipitation",
        unit_of_measurement=None,
        icon="mdi:weather-cloudy-alert",
        device_class=None,
        state_class=None,
        key=key,
    )

    assert sensor.icon == "mdi:weather-cloudy-alert"

    # A valid dry interval remains current until its exclusive end boundary.
    payload["data"] = [{"timestamp": 1699999701, "precipitationrate": 0.0}]
    assert sensor.icon == "mdi:weather-sunny"
    freezer.tick(timedelta(seconds=1))
    assert sensor.icon == "mdi:weather-cloudy-alert"


@pytest.mark.asyncio
async def test_buienalarm_entity_unique_id_attribute(hass: HomeAssistant) -> None:
    """Verify BuienalarmEntity sets _attr_unique_id correctly without property override conflicts."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Unique ID Test",
        unique_id="52.3702_4.8952",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    sensor_key = "nowcastmessage"
    entity = BuienalarmEntity(coordinator, entry, sensor_key)

    expected_uid = f"{entry.entry_id}_{sensor_key}"
    assert entity._attr_unique_id == expected_uid
    assert entity.unique_id == expected_uid


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_rate",
    [float("nan"), float("inf"), -float("inf"), None, True, "invalid", 10**400],
    ids=[
        "nan",
        "infinity",
        "negative-infinity",
        "missing",
        "boolean",
        "malformed",
        "overflow",
    ],
)
async def test_precipitation_periods_split_at_invalid_rate(
    hass: HomeAssistant, freezer, invalid_rate: object
) -> None:
    """Unknown bins separate rain periods without contributing to their averages."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    freezer.move_to("2026-10-22T12:00:00Z")
    coordinator = MagicMock()
    entity = BuienalarmEntity(
        coordinator, MockConfigEntry(domain=DOMAIN, data={}), "precipitation_periods"
    )
    start_ts = datetime.now(timezone.utc).timestamp()
    coordinator.data = {
        "timeseries": {
            "data": [
                {"timestamp": start_ts + i * 300, "precipitationrate": rate}
                for i, rate in enumerate([2.0, invalid_rate, 4.0, 0.0])
            ]
        }
    }

    periods = entity.get_precipitation_periods_as_dict()
    assert len(periods) == 2
    for period, offset, rate in zip(periods, [0, 600], [2.0, 4.0], strict=True):
        assert datetime.fromisoformat(period["start"]) == datetime.fromtimestamp(
            start_ts + offset, timezone.utc
        )
        assert datetime.fromisoformat(period["stop"]) == datetime.fromtimestamp(
            start_ts + offset + 300, timezone.utc
        )
        assert period["duration"] == 5
        assert period["precipitationrate"] == pytest.approx(rate)
    assert entity.get_data("precipitation_periods") == 2


@pytest.mark.asyncio
async def test_precipitation_periods_handles_custom_mapping_data_points(
    hass: HomeAssistant,
) -> None:
    """Verify _get_precipitation_periods processes forecast entries provided as UserDict/Mapping objects."""
    from collections import UserDict
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm UserDict Periods Test",
        unique_id="test_userdict_periods",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "precipitation_periods")

    now_ts = int(datetime.now(timezone.utc).timestamp())

    coordinator.data = {
        "data": [
            UserDict(
                {
                    "timestamp": now_ts + 60,
                    "precipitationrate": 2.5,
                    "precipitationtype": "rain",
                }
            ),
            UserDict(
                {
                    "timestamp": now_ts + 360,
                    "precipitationrate": 1.5,
                    "precipitationtype": "rain",
                }
            ),
            UserDict(
                {
                    "timestamp": now_ts + 660,
                    "precipitationrate": 0.0,
                    "precipitationtype": "rain",
                }
            ),
        ]
    }

    periods = entity._get_precipitation_periods()
    assert len(periods) == 1
    assert periods[0]["duration_minutes"] == 10
    assert periods[0]["precipitationrate"] == 2.0

    dict_periods = entity.get_precipitation_periods_as_dict()
    assert len(dict_periods) == 1
    assert dict_periods[0]["duration"] == 10
    assert dict_periods[0]["precipitationrate"] == 2.0
    assert "start" in dict_periods[0]
    assert "stop" in dict_periods[0]

    assert entity.get_data("precipitation_periods") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("next_precipitation", 0, "mdi:weather-pouring"),
        ("next_precipitation", 15, "mdi:clock-start"),
        ("next_precipitation", None, "mdi:weather-sunny"),
        ("precipitation_duration", 10, "mdi:weather-pouring"),
        ("precipitation_duration", 0, "mdi:weather-sunny"),
    ],
)
async def test_timing_sensor_dynamic_icons(hass, key, value, expected):
    """Timing sensor icons follow validated forecast state."""
    from unittest.mock import MagicMock, patch
    from custom_components.buienalarm.sensor import BuienalarmSensor

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Timing icons",
        unique_id="timing_icons",
        data={"latitude": 52.37, "longitude": 4.89},
    )
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "data": [
            {
                "timestamp": int(datetime.now(timezone.utc).timestamp()) - 60,
                "precipitationrate": 0.0,
            }
        ]
    }
    entity = BuienalarmSensor(
        coordinator,
        entry,
        name=key,
        unit_of_measurement="min",
        icon="mdi:clock-outline",
        device_class=None,
        state_class=None,
        key=key,
    )
    with patch.object(
        BuienalarmSensor,
        "native_value",
        new_callable=lambda: property(lambda self: value),
    ):
        assert entity.icon == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "forecast",
    [
        [],
        None,
        [{"timestamp": "invalid", "precipitationrate": 2.0}],
        [
            {
                "timestamp": int(datetime.now(timezone.utc).timestamp()) - 60,
                "precipitationrate": float("nan"),
            }
        ],
    ],
)
async def test_timing_sensor_icon_fallback_for_invalid_forecast(hass, forecast):
    """Do not report clear skies from missing or malformed forecast data."""
    from unittest.mock import MagicMock, patch
    from custom_components.buienalarm.sensor import BuienalarmSensor

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Timing icons",
        unique_id="timing_icons_fallback",
        data={"latitude": 52.37, "longitude": 4.89},
    )
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"data": forecast}
    entity = BuienalarmSensor(
        coordinator,
        entry,
        name="Next precipitation",
        unit_of_measurement="min",
        icon="mdi:clock-outline",
        device_class=None,
        state_class=None,
        key="next_precipitation",
    )
    with patch.object(
        BuienalarmSensor,
        "native_value",
        new_callable=lambda: property(lambda self: None),
    ):
        assert entity.icon == "mdi:clock-outline"


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["next_precipitation", "precipitation_duration"])
@pytest.mark.parametrize(
    ("stamp_type", "value", "expected_icon"),
    [
        ("offset", -3600.0, "mdi:clock-outline"),  # Expired (-1 hr)
        ("offset", 3600.0, "mdi:clock-outline"),  # Future (+1 hr)
        (
            "offset",
            -300.0,
            "mdi:clock-outline",
        ),  # Exact boundary: max_ts + 300 == now_ts (expired)
        (
            "offset",
            1.0,
            "mdi:clock-outline",
        ),  # Exact boundary: min_ts > now_ts (future)
        (
            "offset",
            0.0,
            "mdi:weather-sunny",
        ),  # Exact boundary: min_ts == now_ts (active)
        ("absolute", -10.0, "mdi:clock-outline"),  # Timestamp < 0
        ("absolute", 253402300800.0, "mdi:clock-outline"),  # Timestamp > 253402300799
        ("absolute", 1e300, "mdi:clock-outline"),  # Non-finite / overflow
    ],
)
async def test_timing_icons_temporal_and_bounds_validation(
    hass, key, stamp_type, value, expected_icon, freezer
):
    """Verify icon evaluation behavior for out-of-bounds, expired, future, and boundary timestamps."""
    from unittest.mock import MagicMock, patch
    from custom_components.buienalarm.sensor import BuienalarmSensor

    freezer.move_to("2026-10-22T12:00:00Z")

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Temporal timing icons",
        unique_id="temporal_icons",
        data={"latitude": 52.37, "longitude": 4.89},
    )
    coordinator = MagicMock()
    coordinator.last_update_success = True

    now_ts = datetime.now(timezone.utc).timestamp()
    stamp = now_ts + value if stamp_type == "offset" else value

    coordinator.data = {"data": [{"timestamp": stamp, "precipitationrate": 0.0}]}
    entity = BuienalarmSensor(
        coordinator,
        entry,
        name=key,
        unit_of_measurement="min",
        icon="mdi:clock-outline",
        device_class=None,
        state_class=None,
        key=key,
    )
    with patch.object(
        BuienalarmSensor,
        "native_value",
        property(lambda self: None if key == "next_precipitation" else 0),
    ):
        assert entity.icon == expected_icon


@pytest.mark.asyncio
async def test_buienalarm_entity_wet_snow_and_mix_precipitation_type_handling(
    hass: HomeAssistant,
) -> None:
    """Verify get_current_precipitation_type and get_current_precipitation_rate_desc handle wet snow and mix correctly."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Buienalarm Wet Snow Mix Test",
        unique_id="test_wet_snow_mix",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "precipitationtype_now")

    now_ts = int(datetime.now(timezone.utc).timestamp())

    # 1. Test "wet snow"
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": 1.5,
                "precipitationtype": "wet snow",
            }
        ]
    }

    assert entity.get_current_precipitation_type() == "Sneeuw"
    assert entity.get_current_precipitation_rate_desc() == "Lichte sneeuw"

    # 2. Test "mix"
    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": 1.5,
                "precipitationtype": "mix",
            }
        ]
    }

    assert entity.get_current_precipitation_type() == "Mix van regen en sneeuw"
    assert entity.get_current_precipitation_rate_desc() == "Lichte regen en sneeuw"


@pytest.mark.parametrize("valid_rate", [0.0, 1.2], ids=["dry", "rain"])
@pytest.mark.parametrize(
    "invalid_rate",
    [float("nan"), float("inf"), -float("inf")],
    ids=["nan", "inf", "-inf"],
)
@pytest.mark.parametrize(
    ("invalid_offset", "unknown_hours"),
    [(-300, ()), (300, (1, 2)), (3600, (2,)), (7200, ())],
    ids=["expired", "both-windows", "two-hour-only", "exclusive-endpoint"],
)
@pytest.mark.asyncio
async def test_aggregate_sensor_states_with_non_finite_rate(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    valid_rate: float,
    invalid_rate: float,
    invalid_offset: int,
    unknown_hours: tuple[int, ...],
) -> None:
    """Keep aggregates unknown only when an included rate is non-finite."""
    freezer.move_to("2026-10-22T12:00:00Z")
    start_ts = datetime.now(timezone.utc).timestamp()
    data = [
        {
            "timestamp": start_ts + index * 300,
            "precipitationrate": (
                invalid_rate if index * 300 == invalid_offset else valid_rate
            ),
            "precipitationtype": "rain",
        }
        for index in range(24)
    ]
    if invalid_offset < 0 or invalid_offset >= 7200:
        data.append(
            {
                "timestamp": start_ts + invalid_offset,
                "precipitationrate": invalid_rate,
                "precipitationtype": "rain",
            }
        )
    response = AsyncMock()
    response.__aenter__.return_value = response
    response.status = 200
    response.headers = {"Content-Type": "application/json", "Age": "0"}
    response.json.return_value = {
        "data": data,
        "nowcastmessage": {"nl": "Verwachting"},
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Aggregate validity test",
        unique_id="aggregate_validity",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )
    entry.add_to_hass(hass)

    with patch("aiohttp.ClientSession.get", return_value=response):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    registry = async_get_entity_registry(hass)
    for hours, key in ((1, "precipitationrate_hour"), (2, "precipitationrate_total")):
        entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"{entry.entry_id}_{key}"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        if hours in unknown_hours:
            assert state.state == STATE_UNKNOWN
        else:
            assert float(state.state) == pytest.approx(valid_rate)


@pytest.mark.asyncio
async def test_calculate_total_precipitation_rate_non_finite_values_and_window_boundaries(
    hass: HomeAssistant, freezer
) -> None:
    """Keep invalid windows unknown and exclude bins starting at end_time."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    freezer.move_to("2026-10-22T12:00:00Z")

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Non-finite Rate Test",
        unique_id="test_non_finite_rates",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "precipitationrate_hour")

    now = datetime.now(timezone.utc)
    start_ts = int(now.timestamp())

    # 1. Non-finite values in forecast data
    coordinator.data = {
        "data": [
            {
                "timestamp": start_ts,
                "precipitationrate": float("nan"),
            },
            {
                "timestamp": start_ts + 300,
                "precipitationrate": float("inf"),
            },
            {
                "timestamp": start_ts + 600,
                "precipitationrate": 1.2,
            },
        ]
    }

    # A valid bin cannot make an aggregate known when other included rates are invalid.
    assert entity.get_total_precipitation_rate_for_next_hour() is None

    # 2. Window boundary check: exactly 12 bins for 1 hour (12:00:00 to 13:00:00)
    # Bins at 12:00, 12:05, ..., 12:55 (12 bins with rate 1.2 mm/h)
    # Plus bin at 13:00 (13th bin with rate 10.0 mm/h, which starts at end_time)
    data = [
        {
            "timestamp": start_ts + (i * 300),
            "precipitationrate": 1.2,
        }
        for i in range(12)
    ]
    # Add 13th bin at 13:00:00
    data.append(
        {
            "timestamp": start_ts + (12 * 300),
            "precipitationrate": 10.0,
        }
    )

    coordinator.data = {"data": data}

    # Twelve five-minute bins at 1.2 mm/h average 1.2 mm/h over the hour.
    assert entity.get_total_precipitation_rate_for_next_hour() == pytest.approx(1.2)


@pytest.mark.parametrize("hours", [1, 2])
@pytest.mark.parametrize(
    ("rates", "expected"),
    [
        ([float("nan"), float("inf"), -float("inf")], None),
        ([0.0, 0.0, 0.0], 0.0),
        ([float("nan"), 0.0, float("inf")], None),
        ([], None),
    ],
    ids=["only-non-finite", "valid-zero", "zero-with-invalid", "empty"],
)
@pytest.mark.asyncio
async def test_total_precipitation_rate_distinguishes_missing_and_zero(
    hass: HomeAssistant, freezer, hours: int, rates: list[float], expected: float | None
) -> None:
    """Keep missing rates unknown while exposing valid dry forecasts as zero."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    freezer.move_to("2026-10-22T12:00:00Z")
    entry = MockConfigEntry(domain=DOMAIN, data={})
    coordinator = MagicMock()
    key = "precipitationrate_hour" if hours == 1 else "precipitationrate_total"
    entity = BuienalarmEntity(coordinator, entry, key)
    start_ts = datetime.now(timezone.utc).timestamp()
    coordinator.data = {
        "timeseries": {
            "data": [
                {"timestamp": start_ts + i * 300, "precipitationrate": rate}
                for i, rate in enumerate(rates)
            ]
        }
    }

    result = entity.get_data(key)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


@pytest.mark.parametrize(("hours", "expected"), [(1, 0.8), (2, 0.4)])
@pytest.mark.asyncio
async def test_total_precipitation_rate_weights_partial_bins(
    hass: HomeAssistant, freezer, hours: int, expected: float
) -> None:
    """Weight only the portions of five-minute bins overlapping the window."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    freezer.move_to("2026-10-22T12:00:00Z")
    entry = MockConfigEntry(domain=DOMAIN, data={})
    coordinator = MagicMock()
    key = "precipitationrate_hour" if hours == 1 else "precipitationrate_total"
    entity = BuienalarmEntity(coordinator, entry, key)
    start_ts = datetime.now(timezone.utc).timestamp()
    end_ts = start_ts + hours * 3600
    coordinator.data = {
        "data": [
            {"timestamp": start_ts - 300, "precipitationrate": 100.0},
            {"timestamp": start_ts - 120, "precipitationrate": 12.0},
            {"timestamp": end_ts - 120, "precipitationrate": 6.0},
            {"timestamp": end_ts, "precipitationrate": 100.0},
        ]
    }

    # Three minutes at 12 mm/h plus two at 6 mm/h yield 0.8 mm.
    assert entity.get_data(key) == pytest.approx(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("wrapped", [False, True], ids=["unwrapped", "wrapped"])
@pytest.mark.parametrize(
    "invalid_timestamp",
    [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "positive-infinity", "negative-infinity"],
)
async def test_precipitation_periods_skip_non_finite_timestamps(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    wrapped: bool,
    invalid_timestamp: float,
) -> None:
    """Skip non-finite timestamps without losing later valid rain periods."""
    from datetime import timedelta
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    freezer.move_to("2026-10-22T12:00:00Z")
    start_time = datetime.now(timezone.utc)
    start_timestamp = start_time.timestamp()
    config_entry = MockConfigEntry(domain=DOMAIN, data={})
    coordinator = MagicMock()
    forecast_payload = {
        "data": [
            {"timestamp": invalid_timestamp, "precipitationrate": 1.0},
            {"timestamp": start_timestamp, "precipitationrate": 1.2},
            {"timestamp": start_timestamp + 300, "precipitationrate": 0.0},
            {"timestamp": invalid_timestamp, "precipitationrate": 1.0},
            {"timestamp": start_timestamp + 600, "precipitationrate": 2.4},
            {"timestamp": start_timestamp + 900, "precipitationrate": 0.0},
        ]
    }
    coordinator.data = {"timeseries": forecast_payload} if wrapped else forecast_payload
    entity = BuienalarmEntity(coordinator, config_entry, "precipitation_periods")

    periods = entity._get_precipitation_periods()

    assert [
        (period["start"], period["stop"], period["duration_minutes"])
        for period in periods
    ] == [
        (start_time, start_time + timedelta(minutes=5), 5),
        (start_time + timedelta(minutes=10), start_time + timedelta(minutes=15), 5),
    ]
    assert [period["precipitationrate"] for period in periods] == pytest.approx(
        [1.2, 2.4]
    )
    assert entity.get_data("precipitation_periods") == 2


@pytest.mark.asyncio
async def test_buienalarm_entity_oversized_integer_overflow_handling(
    hass: HomeAssistant,
) -> None:
    """Verify get_rain_start_time_and_duration and get_mycastmessage handle oversized integer overflow gracefully."""
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Overflow Handling Test",
        unique_id="test_overflow_handling",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "mycastmessage")

    now_ts = int(datetime.now(timezone.utc).timestamp())

    coordinator.data = {
        "data": [
            {
                "timestamp": 10**400,
                "precipitationrate": 1.0,
            },
            {
                "timestamp": now_ts + 300,
                "precipitationrate": 10**400,
            },
            {
                "timestamp": now_ts + 600,
                "precipitationrate": 2.5,
                "precipitationtype": "rain",
            },
            {
                "timestamp": now_ts + 900,
                "precipitationrate": 0.0,
                "precipitationtype": "rain",
            },
        ]
    }

    start, stop, restart, dur, stopped = entity.get_rain_start_time_and_duration(
        coordinator.data["data"]
    )
    assert start is not None
    assert dur == 5

    msg = entity.get_mycastmessage()
    assert msg is not None
    assert msg != "Geen data"


@pytest.mark.asyncio
@pytest.mark.parametrize("wrapped", [False, True], ids=["unwrapped", "wrapped"])
@pytest.mark.parametrize(
    "conversion_error",
    [ValueError, OverflowError, OSError],
    ids=["value_error", "overflow_error", "os_error"],
)
@pytest.mark.parametrize("invalid_first", [True, False], ids=["first", "last"])
async def test_mycastmessage_skips_unconvertible_timestamps(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    monkeypatch: pytest.MonkeyPatch,
    wrapped: bool,
    conversion_error: type[Exception],
    invalid_first: bool,
) -> None:
    """Reject platform-invalid timestamps before they alter valid rain boundaries."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    freezer.move_to("2026-10-24T12:00:00Z")
    start_time = datetime.now(timezone.utc)
    stop_time = start_time + timedelta(minutes=5)
    unsupported_timestamp = 253402300799.0
    original_fromtimestamp = datetime.fromtimestamp

    def fromtimestamp_with_platform_limit(
        timestamp: float, tz: tzinfo | None = None
    ) -> datetime:
        """Simulate a platform rejecting a timestamp within the numeric bounds."""
        if timestamp == unsupported_timestamp:
            raise conversion_error("Timestamp outside the platform datetime range")
        return original_fromtimestamp(timestamp, tz=tz)

    monkeypatch.setattr(
        "custom_components.buienalarm.entity.datetime.fromtimestamp",
        staticmethod(fromtimestamp_with_platform_limit),
    )

    invalid_point = {
        "timestamp": unsupported_timestamp,
        "precipitationrate": 1.0,
    }
    forecast = [
        {"timestamp": start_time.timestamp(), "precipitationrate": 1.0},
        {
            "timestamp": stop_time.timestamp(),
            "precipitationrate": 0.0 if invalid_first else 1.0,
        },
    ]
    forecast.insert(0 if invalid_first else len(forecast), invalid_point)
    payload = {"data": forecast}
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.device_info = {}
    coordinator.data = {"timeseries": payload} if wrapped else payload
    entry = MockConfigEntry(domain=DOMAIN, data={})
    sensor = BuienalarmSensor(
        coordinator,
        entry,
        name="Test forecast",
        unit_of_measurement=None,
        icon=None,
        device_class=None,
        state_class=None,
        key="mycastmessage",
    )

    assert sensor.available is True
    assert sensor.get_rain_start_time_and_duration(forecast) == (
        start_time,
        stop_time if invalid_first else None,
        None,
        5,
        invalid_first,
    )
    expected_message = "Neerslag duurt nog 5 minuten"
    if invalid_first:
        expected_message += f" en stopt rond {sensor.format_time(stop_time)}"
    assert sensor.native_value == expected_message


@pytest.mark.asyncio
@pytest.mark.parametrize("wrapped", [False, True], ids=["unwrapped", "wrapped"])
@pytest.mark.parametrize("conversion_error", [ValueError, OverflowError, OSError])
async def test_mycastmessage_unknown_without_convertible_future_points(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    monkeypatch: pytest.MonkeyPatch,
    wrapped: bool,
    conversion_error: type[Exception],
) -> None:
    """Unconvertible future timestamps cannot turn an expired forecast into dry data."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    freezer.move_to("2026-10-24T12:00:00Z")
    now_ts = datetime.now(timezone.utc).timestamp()
    unsupported_timestamp = 253402300799.0
    original_fromtimestamp = datetime.fromtimestamp

    def fromtimestamp_with_platform_limit(
        timestamp: float, tz: tzinfo | None = None
    ) -> datetime:
        """Reject an otherwise numerically valid future timestamp."""
        if timestamp == unsupported_timestamp:
            raise conversion_error("Timestamp outside the platform datetime range")
        return original_fromtimestamp(timestamp, tz=tz)

    monkeypatch.setattr(
        "custom_components.buienalarm.entity.datetime.fromtimestamp",
        staticmethod(fromtimestamp_with_platform_limit),
    )
    forecast = [
        {"timestamp": now_ts - 300, "precipitationrate": 0.0},
        {"timestamp": unsupported_timestamp, "precipitationrate": 1.0},
    ]
    coordinator = MagicMock()
    coordinator.last_update_success = True
    payload = {"data": forecast}
    coordinator.data = {"timeseries": payload} if wrapped else payload
    sensor = BuienalarmSensor(
        coordinator,
        MockConfigEntry(domain=DOMAIN, data={}),
        name="Test forecast",
        unit_of_measurement=None,
        icon=None,
        device_class=None,
        state_class=None,
        key="mycastmessage",
    )

    assert sensor.get_rain_start_time_and_duration(forecast) is None
    assert sensor.native_value is None
    assert sensor.available is False

    # An ongoing, successfully converted dry bin restores a known forecast.
    forecast.append({"timestamp": now_ts - 299, "precipitationrate": 0.0})
    assert sensor.available is True
    assert sensor.native_value == "Geen neerslag"


@pytest.mark.asyncio
@pytest.mark.parametrize("wrapped", [False, True], ids=["unwrapped", "wrapped"])
@pytest.mark.parametrize(
    "rate_fields",
    [
        {},
        {"precipitationrate": None},
        {"precipitationrate": True},
        {"precipitationrate": "invalid"},
        {"precipitationrate": 10**400},
        {"precipitationrate": -(10**400)},
        {"precipitationrate": "1e400"},
        {"precipitationrate": float("nan")},
        {"precipitationrate": float("inf")},
        {"precipitationrate": -float("inf")},
        {"precipitationrate": -1.0},
    ],
    ids=[
        "missing",
        "null",
        "boolean",
        "malformed",
        "overflow",
        "negative-overflow",
        "string-overflow",
        "nan",
        "infinity",
        "negative-infinity",
        "negative",
    ],
)
async def test_mycastmessage_invalid_rates_do_not_establish_boundaries(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    wrapped: bool,
    rate_fields: dict[str, object],
) -> None:
    """Invalid rates establish neither dry forecasts nor rain-stop or end times."""
    from collections import UserDict
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    freezer.move_to("2026-10-24T12:00:00Z")
    start_time = datetime.now(timezone.utc)
    now_ts = start_time.timestamp()
    invalid_points = [
        {"timestamp": now_ts + 300, **rate_fields},
        UserDict({"timestamp": now_ts + 900, **rate_fields}),
    ]
    forecast = [
        {"timestamp": now_ts, "precipitationrate": 1.0},
        invalid_points[0],
        {"timestamp": now_ts + 600, "precipitationrate": 1.0},
        invalid_points[1],
    ]
    payload = {"data": forecast}
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"timeseries": payload} if wrapped else payload
    sensor = BuienalarmSensor(
        coordinator,
        MockConfigEntry(domain=DOMAIN, data={}),
        name="Test forecast",
        unit_of_measurement=None,
        icon=None,
        device_class=None,
        state_class=None,
        key="mycastmessage",
    )

    assert sensor.available is True
    assert sensor.get_rain_start_time_and_duration(forecast) == (
        start_time,
        None,
        None,
        10,
        False,
    )
    assert sensor.native_value == "Neerslag duurt nog 10 minuten"

    # Only an explicitly valid zero rate can establish the stop boundary.
    stop_time = start_time + timedelta(minutes=20)
    forecast.append({"timestamp": stop_time.timestamp(), "precipitationrate": 0.0})
    assert sensor.get_rain_start_time_and_duration(forecast) == (
        start_time,
        stop_time,
        None,
        20,
        True,
    )

    payload["data"] = invalid_points
    assert sensor.get_rain_start_time_and_duration(invalid_points) is None
    assert sensor.native_value is None
    assert sensor.available is False


@pytest.mark.asyncio
async def test_get_precipitation_duration_when_currently_dry_and_rain_upcoming(
    hass: HomeAssistant,
) -> None:
    """Verify get_precipitation_duration calculates upcoming rain duration when currently dry."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Upcoming Rain Duration Test",
        unique_id="test_upcoming_duration",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "precipitation_duration")

    now_ts = int(datetime.now(timezone.utc).timestamp())

    # Current bin dry, rain starts in 10 minutes (now_ts + 600) and lasts 15 minutes (3 bins of rain)
    coordinator.data = {
        "data": [
            {"timestamp": now_ts, "precipitationrate": 0.0},
            {"timestamp": now_ts + 300, "precipitationrate": 0.0},
            {
                "timestamp": now_ts + 600,
                "precipitationrate": 2.0,
                "precipitationtype": "rain",
            },
            {
                "timestamp": now_ts + 900,
                "precipitationrate": 3.0,
                "precipitationtype": "rain",
            },
            {
                "timestamp": now_ts + 1200,
                "precipitationrate": 1.0,
                "precipitationtype": "rain",
            },
            {
                "timestamp": now_ts + 1500,
                "precipitationrate": 0.0,
                "precipitationtype": "rain",
            },
        ]
    }

    assert entity.get_precipitation_duration() == 15


@pytest.mark.parametrize(
    ("raw_type", "expected_type", "expected_desc"),
    [
        ("  RAIN ", "Regen", "Lichte regen"),
        ("  SNOW ", "Sneeuw", "Lichte sneeuw"),
        (" MIX ", "Mix van regen en sneeuw", "Lichte regen en sneeuw"),
    ],
)
@pytest.mark.asyncio
async def test_precipitation_type_string_normalization(
    hass: HomeAssistant,
    raw_type: str,
    expected_type: str,
    expected_desc: str,
) -> None:
    """Verify precipitationtype string normalization handles whitespace and case variations."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="String Normalization Test",
        unique_id="test_type_normalization",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    entity = BuienalarmEntity(coordinator, entry, "precipitationtype_now")

    now_ts = int(datetime.now(timezone.utc).timestamp())

    coordinator.data = {
        "data": [
            {
                "timestamp": now_ts,
                "precipitationrate": 2.0,
                "precipitationtype": raw_type,
            }
        ]
    }
    assert entity.get_current_precipitation_type() == expected_type
    assert entity.get_current_precipitation_rate_desc() == expected_desc


@pytest.mark.asyncio
async def test_precipitation_periods_disabled_by_default(
    hass: HomeAssistant,
) -> None:
    """Verify precipitation_periods entity registry disabled default is set to False."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.sensor import BuienalarmSensor

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Disabled Default Test",
        unique_id="test_disabled_default",
        data={"latitude": 52.3702, "longitude": 4.8952},
    )

    coordinator = MagicMock()
    coordinator.last_update_success = True

    sensor = BuienalarmSensor(
        coordinator,
        entry,
        name="Neerslag periodes",
        unit_of_measurement=None,
        icon="mdi:weather-rainy",
        device_class=None,
        state_class=None,
        key="precipitation_periods",
        translation_key="precipitation_periods",
        enabled_by_default=False,
    )

    assert sensor.entity_registry_enabled_default is False


def test_forecast_duration_metadata_excludes_measurement_statistics() -> None:
    """Keep forecast duration out of measurement statistics in both descriptions."""
    duration_config = next(
        sensor_config
        for sensor_config in SENSORS
        if sensor_config["key"] == "precipitation_duration"
    )
    duration_description = next(
        description
        for description in SENSOR_DESCRIPTIONS
        if description.key == "precipitation_duration"
    )
    assert duration_config["state_class"] is None
    assert duration_description.state_class is None


@pytest.mark.parametrize("invalid_rate", [-1.0, None, "invalid", float("nan"), True])
@pytest.mark.asyncio
async def test_current_readings_skip_invalid_active_points(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    invalid_rate: object,
) -> None:
    """Retain a valid current reading after an invalid point in the same bin."""
    from unittest.mock import MagicMock
    from custom_components.buienalarm.entity import BuienalarmEntity

    freezer.move_to("2026-10-23T12:00:00Z")
    timestamp = datetime.now(timezone.utc).timestamp()
    coordinator = MagicMock()
    coordinator.data = {
        "data": [
            {
                "timestamp": timestamp,
                "precipitationrate": invalid_rate,
                "precipitationtype": "snow",
            },
            {
                "timestamp": timestamp,
                "precipitationrate": 2.5,
                "precipitationtype": "  RAIN ",
            },
        ]
    }
    entity = BuienalarmEntity(
        coordinator, MockConfigEntry(domain=DOMAIN, data={}), "precipitationrate_now"
    )

    assert entity.get_current_precipitation() == pytest.approx(2.5)
    assert entity.get_current_precipitation_type() == "Regen"
    assert entity.get_current_precipitation_rate_desc() == "Matige regen"
    assert entity.get_next_precipitation() == 0
