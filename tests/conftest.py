import sys
import os

import pytest
from homeassistant.core import HomeAssistant

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture
async def config_data() -> dict:
    """Provide default config data for tests."""
    return {
        "username": "testuser",
        "password": "testpass",
        "station": "utrecht",
    }

# De 'hass' fixture wordt geleverd door pytest-homeassistant-custom-component plugin
# Je hoeft deze niet zelf te definiëren, maar je kunt hier wel extra setup doen als nodig.

@pytest.fixture
async def hass_with_integration(hass: HomeAssistant, config_data: dict) -> HomeAssistant:
    """Fixture to setup the integration for tests."""
    # Als je setup nodig hebt, zoals async_setup_component kan je dat hier doen
    # Bijvoorbeeld:
    # await async_setup_component(hass, "http", {})
    # Je kan hier ook config entries toevoegen als je wil

    return hass
