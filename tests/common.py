# tests/common.py
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from typing import Any
from uuid import uuid4

from custom_components.buienalarm.const import DOMAIN


class MockConfigEntry(ConfigEntry):
    """A mock ConfigEntry for testing."""

    def __init__(
        self,
        *,
        entry_id: str | None = None,
        domain: str = DOMAIN,
        title: str = "Mock Title",
        data: dict[str, Any] = {},
        options: dict[str, Any] = {},
        source: str = "user",
        version: int = 1,
        unique_id: str | None = None,
        disabled_by: str | None = None,
    ) -> None:
        """Initialize the config entry."""
        super().__init__(
            version=version,
            domain=domain,
            title=title,
            data=data,
            source=source,
            options=options,
            entry_id=entry_id or str(uuid4()),
            unique_id=unique_id,
            disabled_by=disabled_by,
        )

    def add_to_hass(self, hass: HomeAssistant) -> None:
        """Add the config entry to hass for testing."""
        if DOMAIN not in hass.config_entries._entries:
            hass.config_entries._entries[DOMAIN] = []
        hass.config_entries._entries[DOMAIN].append(self)
        hass.config_entries._entries[self.entry_id] = self
        self.hass = hass
