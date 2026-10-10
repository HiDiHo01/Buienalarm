from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTime, UnitOfVolumetricFlux

from custom_components.buienalarm.const import (
    API_CONF_URL,
    API_ENDPOINT,
    API_TIMEOUT,
    API_TIMEZONE,
    ATTR_ATTRIBUTION,
    BINARY_SENSOR,
    DATA_KEY,
    DATA_REFRESH_INTERVAL,
    DEFAULT_NAME,
    DOMAIN,
    NAME,
    PLATFORMS,
    SCAN_INTERVAL,
    SENSOR,
    SENSORS,
    VERSION,
)


def test_api_constants():
    """Test the API-related constants."""
    assert (
        API_ENDPOINT
        == "https://imn-rust-lb.infoplaza.io/v4/nowcast/ba/timeseries/{}/{}"
    )

    assert API_TIMEOUT == 30
    assert API_TIMEZONE == "Europe/Amsterdam"
    assert API_CONF_URL == "https://buienalarm.nl"
    assert DATA_KEY == "data"


def test_base_component_constants():
    """Test the base component constants."""
    assert NAME == "Buienalarm"
    assert DOMAIN == "buienalarm"
    assert VERSION == "2026.5.5"
    assert ATTR_ATTRIBUTION == "Data provided by Buienalarm"
    assert DEFAULT_NAME == NAME


def test_refresh_constants():
    """Test the data refresh constants."""
    assert SCAN_INTERVAL == timedelta(minutes=5)
    assert DATA_REFRESH_INTERVAL == 300


def test_platform_constants():
    """Test the platform-related constants."""
    assert BINARY_SENSOR == "binary_sensor"
    assert SENSOR == "sensor"
    assert PLATFORMS == ["binary_sensor", "sensor"]


def test_sensors_structure():
    """Test the structure and content of the SENSORS list."""
    assert isinstance(SENSORS, list)
    assert len(SENSORS) > 0

    for sensor in SENSORS:
        assert isinstance(sensor, dict)
        assert "name" in sensor
        assert "icon" in sensor
        assert "key" in sensor
        assert isinstance(sensor["name"], str)
        assert isinstance(sensor["icon"], str)
        assert isinstance(sensor["key"], str)

        assert sensor["unit_of_measurement"] is None or isinstance(
            sensor["unit_of_measurement"], str
        )

        if sensor["device_class"]:
            assert isinstance(sensor["device_class"], SensorDeviceClass)
        if sensor["state_class"]:
            assert isinstance(sensor["state_class"], SensorStateClass)


def test_units_of_measurement():
    """Test units of measurement used in SENSORS."""
    for sensor in SENSORS:
        if sensor["unit_of_measurement"] == UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR:
            assert (
                sensor["unit_of_measurement"]
                == UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR
            )
        elif sensor["unit_of_measurement"] == UnitOfTime.MINUTES:
            assert sensor["unit_of_measurement"] == UnitOfTime.MINUTES
