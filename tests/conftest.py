import sys
import os
# Voeg de projectroot toe aan sys.path zodat 'custom_components' geïmporteerd kan worden
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import asyncio
import pytest
import pytest_asyncio
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import utcnow
from homeassistant.helpers.typing import ConfigType
from tempfile import TemporaryDirectory

@pytest_asyncio.fixture
async def hass() -> HomeAssistant:
    """Return a Home Assistant instance with temporary config dir."""
    from homeassistant.core import HomeAssistant
    from homeassistant.config import async_process_ha_core_config

    with TemporaryDirectory() as config_dir:
        hass = HomeAssistant(config_dir)

        # Optioneel: stel basisconfig in
        await async_process_ha_core_config(
            hass,
            {
                "name": "Home",
                "latitude": 52.1,
                "longitude": 5.1,
                "elevation": 1,
                "unit_system": "metric",
                "time_zone": "Europe/Amsterdam",
            },
        )

        yield hass
