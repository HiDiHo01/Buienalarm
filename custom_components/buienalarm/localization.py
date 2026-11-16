"""Load and refresh the translations used by Buienalarm's backend text."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.const import EVENT_CORE_CONFIG_UPDATE
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.translation import async_get_translations

from .const import CONF_MESSAGE_LANGUAGE, DOMAIN, MESSAGE_LANGUAGES

if TYPE_CHECKING:
    from .coordinator import BuienalarmConfigEntry, BuienalarmDataUpdateCoordinator


@dataclass(frozen=True)
class BuienalarmLocale:
    """Translations and the forecast message language of one config entry."""

    language: str
    translations: Mapping[str, str]

    def text(self, key: str, /, **placeholders: object) -> str:
        """Format a common translation with its named placeholders."""
        return self.translations[f"component.{DOMAIN}.common.{key}"].format(
            **placeholders
        )


def _selected_language(hass: HomeAssistant, entry: BuienalarmConfigEntry) -> str:
    """Select the entry's fixed language or the configured base language."""
    override = entry.options.get(CONF_MESSAGE_LANGUAGE)
    if isinstance(override, str) and override in MESSAGE_LANGUAGES:
        return override
    return hass.config.language.lower().replace("_", "-").partition("-")[0]


async def _async_load_locale(hass: HomeAssistant, language: str) -> BuienalarmLocale:
    """Load common strings with Home Assistant's English fallback."""
    translations = await async_get_translations(hass, language, "common", {DOMAIN})
    return BuienalarmLocale(
        language if language in MESSAGE_LANGUAGES else "en", translations
    )


async def async_setup_localization(
    hass: HomeAssistant,
    entry: BuienalarmConfigEntry,
    coordinator: BuienalarmDataUpdateCoordinator,
) -> None:
    """Load the initial locale and update cached presentation on language changes."""
    while True:
        loaded_language = _selected_language(hass, entry)
        locale = await _async_load_locale(hass, loaded_language)
        if loaded_language == _selected_language(hass, entry):
            break
    coordinator.locale = locale
    closed = False

    async def _async_set_language(language: str) -> None:
        """Apply a translated snapshot only if its language is still selected."""
        nonlocal loaded_language
        updated_locale = await _async_load_locale(hass, language)
        if (
            not closed
            and language == _selected_language(hass, entry)
            and language != loaded_language
        ):
            loaded_language = language
            coordinator.locale = updated_locale
            coordinator.async_update_listeners()

    @callback
    def _async_config_updated(_event: Event) -> None:
        """Schedule translation only when the selected language changes."""
        language = _selected_language(hass, entry)
        if language != loaded_language:
            entry.async_create_background_task(
                hass, _async_set_language(language), f"{DOMAIN} translations"
            )

    unsubscribe = hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, _async_config_updated)

    @callback
    def _async_close() -> None:
        """Remove the language listener and discard any late results on unload."""
        nonlocal closed
        closed = True
        unsubscribe()

    entry.async_on_unload(_async_close)
