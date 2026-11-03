"""Exercise real Home Assistant APIs independently of the versioned pytest helper."""

from datetime import datetime, timezone
import importlib
from importlib.metadata import version
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from aiohttp import ClientSession, TCPConnector, ThreadedResolver
from homeassistant import loader
from homeassistant.bootstrap import async_load_base_functionality
from homeassistant.config_entries import SOURCE_USER, ConfigEntries, ConfigEntryState
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_setup_component

from custom_components.buienalarm.const import DOMAIN


class LatestHomeAssistantTests(unittest.IsolatedAsyncioTestCase):
    """Check discovery, config-flow validation, platform setup, and unloading."""

    async def asyncSetUp(self) -> None:
        """Create an isolated Home Assistant instance with mocked weather transport."""
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger(__name__).info(
            "Testing Home Assistant %s", version("homeassistant")
        )
        self.config_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.config_directory.cleanup)
        self.hass = HomeAssistant(self.config_directory.name)
        session = ClientSession(connector=TCPConnector(resolver=ThreadedResolver()))
        self.addAsyncCleanup(session.close)
        self.enterContext(
            patch(
                "custom_components.buienalarm.async_get_clientsession",
                autospec=True,
                return_value=session,
            )
        )
        now = int(datetime.now(timezone.utc).timestamp())
        forecast = {
            "nowcastmessage": {"nl": "Geen neerslag"},
            "data": [
                {
                    "timestamp": now + offset,
                    "precipitationrate": 0.0,
                    "precipitationtype": "rain",
                }
                for offset in range(0, 7500, 300)
            ],
        }
        self.enterContext(
            patch(
                "custom_components.buienalarm.api.BuienalarmApiClient.async_get_initial_data",
                new_callable=AsyncMock,
                return_value={},
            )
        )
        self.enterContext(
            patch(
                "custom_components.buienalarm.api.BuienalarmApiClient.async_get_data",
                new_callable=AsyncMock,
                return_value=forecast,
            )
        )
        self.addAsyncCleanup(self.hass.async_stop, force=True)
        loader.async_setup(self.hass)
        self.hass.config_entries = ConfigEntries(self.hass, {})
        self.assertTrue(await async_load_base_functionality(self.hass))
        await self.hass.config.async_set_time_zone("Europe/Amsterdam")
        self.assertTrue(await async_setup_component(self.hass, "homeassistant", {}))

    async def test_integration_modules_and_discovery(self) -> None:
        """Import every integration module and discover the actual manifest."""
        package_directory = (
            Path(__file__).resolve().parents[1] / "custom_components" / DOMAIN
        )
        for module_file in package_directory.glob("*.py"):
            with self.subTest(module=module_file.stem):
                module_name = f"custom_components.{DOMAIN}"
                if module_file.stem != "__init__":
                    module_name += f".{module_file.stem}"
                importlib.import_module(module_name)
        integration = await async_get_integration(self.hass, DOMAIN)
        self.assertEqual(integration.domain, DOMAIN)

    async def test_invalid_coordinates_remain_a_form_error(self) -> None:
        """Reject an out-of-range coordinate through Home Assistant's flow manager."""
        result = await self.hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_NAME: "Compatibility test",
                CONF_LATITUDE: 999.0,
                CONF_LONGITUDE: 5.1,
            },
        )
        self.assertEqual(result["type"], FlowResultType.FORM)
        self.assertEqual(result["errors"], {"base": "invalid_coordinates"})

    async def test_setup_and_unload_sensor_platforms(self) -> None:
        """Create a real config entry and load and unload both entity platforms."""
        result = await self.hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_NAME: "Compatibility test",
                CONF_LATITUDE: 52.1,
                CONF_LONGITUDE: 5.1,
            },
        )
        self.assertEqual(result["type"], FlowResultType.CREATE_ENTRY)
        entry = result["result"]
        await self.hass.async_block_till_done()
        self.assertEqual(entry.state, ConfigEntryState.LOADED)
        self.assertTrue(self.hass.states.async_all("sensor"))
        binary_states = self.hass.states.async_all("binary_sensor")
        self.assertTrue(binary_states)
        self.assertTrue(all(state.state == "off" for state in binary_states))
        precipitation_entity_id = entity_registry.async_get(
            self.hass
        ).async_get_entity_id(
            "sensor", DOMAIN, f"{entry.entry_id}_precipitationrate_total"
        )
        self.assertIsNotNone(precipitation_entity_id)
        precipitation_state = self.hass.states.get(precipitation_entity_id)
        self.assertIsNotNone(precipitation_state)
        self.assertEqual(precipitation_state.state, "0.0")
        self.assertTrue(await self.hass.config_entries.async_unload(entry.entry_id))
        await self.hass.async_block_till_done()
        self.assertEqual(entry.state, ConfigEntryState.NOT_LOADED)
