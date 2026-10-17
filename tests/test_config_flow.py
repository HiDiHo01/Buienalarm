"""Tests for the Buienalarm config and options flow."""

from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.buienalarm.const import DOMAIN


@pytest.fixture(autouse=True)
def mock_api_calls():
    """Mock API calls to avoid socket errors."""
    with patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_initial_data",
        return_value={},
    ), patch(
        "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
        return_value={"data": []},
    ):
        yield


@pytest.mark.asyncio
async def test_options_flow_preserves_data_defaults(hass: HomeAssistant) -> None:
    """Test that options flow initializes defaults from entry.data when entry.options is empty."""
    custom_data = {
        CONF_NAME: "Custom Spot",
        CONF_LATITUDE: 51.5,
        CONF_LONGITUDE: 4.5,
        "notification_limit": 10,
        "refresh_interval": 450,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=custom_data,
        options={},
        unique_id="51.5_4.5",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Verify displayed defaults before submitting any user input.
    defaults = result["data_schema"]({})
    assert defaults[CONF_NAME] == "Custom Spot"
    assert defaults[CONF_LATITUDE] == 51.5
    assert defaults[CONF_LONGITUDE] == 4.5
    assert defaults["notification_limit"] == 10
    assert defaults["refresh_interval"] == 450

    # Save the options form without changing the values that were populated
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Custom Spot",
            CONF_LATITUDE: 51.5,
            CONF_LONGITUDE: 4.5,
            "notification_limit": 10,
            "refresh_interval": 450,
        },
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["refresh_interval"] == 450
    assert entry.options["notification_limit"] == 10
    assert entry.options[CONF_NAME] == "Custom Spot"
    assert entry.options[CONF_LATITUDE] == 51.5
    assert entry.options[CONF_LONGITUDE] == 4.5


@pytest.mark.asyncio
async def test_options_flow_invalid_coordinates(hass: HomeAssistant) -> None:
    """Test that options flow rejects invalid coordinates with error while preserving submitted input."""
    custom_data = {
        CONF_NAME: "Custom Spot",
        CONF_LATITUDE: 51.5,
        CONF_LONGITUDE: 4.5,
        "notification_limit": 10,
        "refresh_interval": 450,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=custom_data,
        options={},
        unique_id="51.5_4.5",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    # Submit invalid coordinates along with modified fields
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Modified Spot",
            CONF_LATITUDE: 999.0,
            CONF_LONGITUDE: 4.5,
            "notification_limit": 20,
            "refresh_interval": 600,
        },
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_coordinates"}

    # Verify that the returned form preserves the attempted user_input values
    defaults = result2["data_schema"]({})
    assert defaults[CONF_NAME] == "Modified Spot"
    assert defaults[CONF_LATITUDE] == 999.0
    assert defaults["notification_limit"] == 20
    assert defaults["refresh_interval"] == 600


@pytest.mark.asyncio
async def test_config_flow_user_step(hass: HomeAssistant) -> None:
    """Test the user configuration flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Test Location",
            CONF_LATITUDE: 52.3,
            CONF_LONGITUDE: 4.9,
            "notification_limit": 0,
            "refresh_interval": 600,
        },
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Test Location (52.3, 4.9)"
    assert result2["data"][CONF_NAME] == "Test Location"
    assert result2["data"][CONF_LATITUDE] == 52.3
    assert result2["data"][CONF_LONGITUDE] == 4.9
    assert result2["data"]["refresh_interval"] == 600


@pytest.mark.parametrize(
    "refresh_interval",
    [float("nan"), float("inf"), float("-inf"), "nan", "inf", "-inf", "1e309"],
)
@pytest.mark.asyncio
async def test_config_flow_rejects_non_finite_refresh_interval(
    hass: HomeAssistant, refresh_interval: float | str
) -> None:
    """Reject non-finite intervals without saving and allow a corrected submission."""
    user_input = {
        CONF_NAME: "Test Location",
        CONF_LATITUDE: 52.3,
        CONF_LONGITUDE: 4.9,
        "notification_limit": 0,
        "refresh_interval": refresh_interval,
    }

    # Initial data reaches the handler without the form schema validating it first.
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=user_input
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"refresh_interval": "invalid_refresh_interval"}
    assert not hass.config_entries.async_entries(DOMAIN)

    user_input["refresh_interval"] = 600
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=user_input
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["refresh_interval"] == 600
    assert isinstance(result["data"]["refresh_interval"], int)


@pytest.mark.parametrize(
    "refresh_interval",
    [float("nan"), float("inf"), float("-inf"), "nan", "inf", "-inf", "1e309"],
)
@pytest.mark.asyncio
async def test_options_flow_rejects_non_finite_refresh_interval(
    hass: HomeAssistant, refresh_interval: float | str
) -> None:
    """Keep saved options intact when rejecting a non-finite refresh interval."""
    user_input = {
        CONF_NAME: "Test Location",
        CONF_LATITUDE: 52.3,
        CONF_LONGITUDE: 4.9,
        "notification_limit": 0,
        "refresh_interval": 450,
    }
    entry = MockConfigEntry(
        domain=DOMAIN, data=user_input.copy(), options=user_input.copy()
    )
    entry.add_to_hass(hass)
    user_input["refresh_interval"] = refresh_interval

    # Initial data reaches the handler without the form schema validating it first.
    result = await hass.config_entries.options.async_init(
        entry.entry_id, data=user_input
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"refresh_interval": "invalid_refresh_interval"}
    assert entry.options["refresh_interval"] == 450
    assert entry.data["refresh_interval"] == 450

    user_input["refresh_interval"] = 600
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=user_input
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["refresh_interval"] == 600
    assert isinstance(entry.options["refresh_interval"], int)


@pytest.mark.asyncio
async def test_config_flow_title_coordinate_rounding(hass: HomeAssistant) -> None:
    """Test that config flow rounds coordinates in entry title to 4 digits."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Buienalarm",
            CONF_LATITUDE: 52.79346889409631,
            CONF_LONGITUDE: 4.792772233486176,
            "notification_limit": 0,
            "refresh_interval": 300,
        },
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Buienalarm (52.7935, 4.7928)"


@pytest.mark.asyncio
async def test_config_flow_default_coordinates_from_hass_config(
    hass: HomeAssistant,
) -> None:
    """Test that config flow defaults to Home Assistant system location coordinates."""
    hass.config.latitude = 52.0
    hass.config.longitude = 5.0

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    defaults = result["data_schema"]({})
    assert defaults[CONF_LATITUDE] == 52.0
    assert defaults[CONF_LONGITUDE] == 5.0


@pytest.mark.asyncio
async def test_config_flow_default_coordinates_zero_latitude(
    hass: HomeAssistant,
) -> None:
    """Test that config flow preserves zero-valued system coordinates (0.0, 5.0)."""
    hass.config.latitude = 0.0
    hass.config.longitude = 5.0

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    defaults = result["data_schema"]({})
    assert defaults[CONF_LATITUDE] == 0.0
    assert defaults[CONF_LONGITUDE] == 5.0


@pytest.mark.asyncio
async def test_options_flow_range_validation(hass: HomeAssistant) -> None:
    """Test that options flow schema enforces range limits on notification_limit and refresh_interval."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Spot",
            CONF_LATITUDE: 52.0,
            CONF_LONGITUDE: 5.0,
        },
        options={},
        unique_id="52.0_5.0",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    # Submit refresh_interval below 60
    with pytest.raises((vol.Invalid, vol.MultipleInvalid)):
        result["data_schema"](
            {
                CONF_NAME: "Spot",
                CONF_LATITUDE: 52.0,
                CONF_LONGITUDE: 5.0,
                "notification_limit": 0,
                "refresh_interval": 10,
            }
        )

    # Submit notification_limit below 0
    with pytest.raises((vol.Invalid, vol.MultipleInvalid)):
        result["data_schema"](
            {
                CONF_NAME: "Spot",
                CONF_LATITUDE: 52.0,
                CONF_LONGITUDE: 5.0,
                "notification_limit": -1,
                "refresh_interval": 300,
            }
        )

    # Submit fractional refresh_interval (e.g. 300.5)
    with pytest.raises((vol.Invalid, vol.MultipleInvalid)):
        result["data_schema"](
            {
                CONF_NAME: "Spot",
                CONF_LATITUDE: 52.0,
                CONF_LONGITUDE: 5.0,
                "notification_limit": 0,
                "refresh_interval": 300.5,
            }
        )

    # Submit fractional notification_limit (e.g. 2.5)
    with pytest.raises((vol.Invalid, vol.MultipleInvalid)):
        result["data_schema"](
            {
                CONF_NAME: "Spot",
                CONF_LATITUDE: 52.0,
                CONF_LONGITUDE: 5.0,
                "notification_limit": 2.5,
                "refresh_interval": 300,
            }
        )
