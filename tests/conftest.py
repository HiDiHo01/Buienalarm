import sys
import os
import pytest
import pytest_asyncio
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest_asyncio.fixture
async def hass() -> HomeAssistant:
    """Create a Home Assistant instance for testing."""
    from homeassistant import setup
    hass = HomeAssistant()
    # Initialize Home Assistant core or any setups here if needed
    await async_setup_component(hass, "http", {})  # Example if HTTP needed

    yield hass

    # Clean up after tests
    await hass.async_stop()
