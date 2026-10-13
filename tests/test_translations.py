"""Test translation files validity and structure."""

import json
from pathlib import Path

from custom_components.buienalarm.sensor_types import (
    BINARY_SENSOR_DESCRIPTIONS,
    SENSOR_DESCRIPTIONS,
)

TRANSLATIONS_DIR = Path("custom_components/buienalarm/translations")


def test_translation_files_exist_and_valid_json():
    """Verify en.json and nl.json exist and are valid JSON."""
    for lang in ["en", "nl"]:
        path = TRANSLATIONS_DIR / f"{lang}.json"
        assert path.exists(), f"{path} should exist"

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "config" in data
        assert "options" in data
        assert "entity" in data

        # Check config flow step user data
        assert "step" in data["config"]
        assert "user" in data["config"]["step"]
        assert "data" in data["config"]["step"]["user"]
        assert "data_description" in data["config"]["step"]["user"]

        # Check options flow step init
        assert "step" in data["options"]
        assert "init" in data["options"]["step"]
        assert "data" in data["options"]["step"]["init"]
        assert "data_description" in data["options"]["step"]["init"]

        # Check error keys
        assert "error" in data["config"]
        assert "invalid_coordinates" in data["config"]["error"]

        # Check binary sensor entity translations
        assert "binary_sensor" in data["entity"]
        assert "currently_raining" in data["entity"]["binary_sensor"]
        assert "precipitation_expected" in data["entity"]["binary_sensor"]

        # Check sensor entity translations
        assert "precipitation_periods" in data["entity"]["sensor"]
        assert "precipitationrate_now_desc" in data["entity"]["sensor"]


def test_flow_translation_parity():
    """Verify config and options flow translations have exact key parity between locales."""
    with open(TRANSLATIONS_DIR / "en.json", "r", encoding="utf-8") as f:
        en_data = json.load(f)
    with open(TRANSLATIONS_DIR / "nl.json", "r", encoding="utf-8") as f:
        nl_data = json.load(f)

    # Config user step key parity
    en_config_user = en_data["config"]["step"]["user"]
    nl_config_user = nl_data["config"]["step"]["user"]
    assert set(en_config_user["data"].keys()) == set(nl_config_user["data"].keys())
    assert set(en_config_user["data_description"].keys()) == set(
        nl_config_user["data_description"].keys()
    )

    # Options init step key parity
    en_options_init = en_data["options"]["step"]["init"]
    nl_options_init = nl_data["options"]["step"]["init"]
    assert set(en_options_init["data"].keys()) == set(nl_options_init["data"].keys())
    assert set(en_options_init["data_description"].keys()) == set(
        nl_options_init["data_description"].keys()
    )


def test_sensors_have_matching_translations():
    """Verify all sensors defined in SENSORS have matching translation keys."""
    import re

    const_path = Path("custom_components/buienalarm/const.py")
    content = const_path.read_text(encoding="utf-8")
    sensor_keys = re.findall(r'"key":\s*"([^"]+)"', content)

    for lang in ["en", "nl"]:
        path = TRANSLATIONS_DIR / f"{lang}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        entity_data = data.get("entity", {})
        assert "binary_sensor" in entity_data
        assert "sensor" in entity_data

        binary_sensor_translations = entity_data["binary_sensor"]
        for bs in BINARY_SENSOR_DESCRIPTIONS:
            translation_key = bs.translation_key or bs.key
            assert (
                translation_key in binary_sensor_translations
            ), f"Missing binary_sensor translation key '{translation_key}' in {lang}.json"
            assert "name" in binary_sensor_translations[translation_key]

        sensor_translations = entity_data["sensor"]
        for s in SENSOR_DESCRIPTIONS:
            translation_key = s.translation_key or s.key
            assert (
                translation_key in sensor_translations
            ), f"Missing sensor translation key '{translation_key}' in {lang}.json"
            assert "name" in sensor_translations[translation_key]

        sensor_translations = data.get("entity", {}).get("sensor", {})

        for key in sensor_keys:
            assert (
                key in sensor_translations
            ), f"Sensor key '{key}' missing in {lang}.json entity.sensor translations"
            assert (
                "name" in sensor_translations[key]
            ), f"Sensor key '{key}' missing 'name' in {lang}.json"
