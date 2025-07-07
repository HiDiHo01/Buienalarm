import pytest
from datetime import timedelta
from homeassistant.const import UnitOfTime, UnitOfVolumetricFlux
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

# Import the constants from your const.py file
from custom_components.buienalarm.const import (
    API_ENDPOINT,
    API_TIMEOUT,
    API_TIMEZONE,
    API_CONF_URL,
    DATA_KEY,
    NAME,
    DOMAIN,
    VERSION,
    ATTR_ATTRIBUTION,
    DEFAULT_NAME,
    SCAN_INTERVAL,
    DATA_REFRESH_INTERVAL,
    SENSOR,
    PLATFORMS,
    SENSORS,
)

def test_api_constants():
    """Test the API-related constants."""
    assert API_ENDPOINT == "https://cdn.buienalarm.nl/api/4.0/nowcast/timeseries/{}/{}"
    assert API_TIMEOUT == 30
    assert API_TIMEZONE == "Europe/Amsterdam"
    assert API_CONF_URL == "https://buienalarm.nl"
    assert DATA_KEY == "data"

def test_base_component_constants():
    """Test the base component constants."""
    assert NAME == "Buienalarm"
    assert DOMAIN == "buienalarm"
    assert VERSION == "2025.7.7"
    assert ATTR_ATTRIBUTION == "Data provided by Buienalarm"
    assert DEFAULT_NAME == NAME

def test_refresh_constants():
    """Test the data refresh constants."""
    assert SCAN_INTERVAL == timedelta(minutes=5)
    assert DATA_REFRESH_INTERVAL == 300

def test_platform_constants():
    """Test the platform-related constants."""
    assert SENSOR == "sensor"
    assert PLATFORMS == ["sensor"]

def test_sensors_structure():
    """Test the structure and content of the SENSORS list."""
    assert isinstance(SENSORS, list)
    assert len(SENSORS) > 0  # Check if there is at least one sensor

    # Check the structure of each sensor in the list
    for sensor in SENSORS:
        assert isinstance(sensor, dict)
        assert "name" in sensor
        assert "icon" in sensor
        assert "key" in sensor
        assert isinstance(sensor["name"], str)
        assert isinstance(sensor["icon"], str)
        assert isinstance(sensor["key"], str)

        # Check that unit_of_measurement is either None or a valid unit
        assert sensor["unit_of_measurement"] is None or isinstance(sensor["unit_of_measurement"], str)

        # Check if device_class and state_class are valid if provided
        if sensor["device_class"]:
            assert isinstance(sensor["device_class"], SensorDeviceClass)
        if sensor["state_class"]:
            assert isinstance(sensor["state_class"], SensorStateClass)

def test_units_of_measurement():
    """Test units of measurement used in SENSORS."""
    for sensor in SENSORS:
        if sensor["unit_of_measurement"] == UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR:
            assert sensor["unit_of_measurement"] == UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR
        elif sensor["unit_of_measurement"] == UnitOfTime.MINUTES:
            assert sensor["unit_of_measurement"] == UnitOfTime.MINUTES
