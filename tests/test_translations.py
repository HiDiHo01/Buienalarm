"""Test translation files validity and structure."""

import json
from pathlib import Path

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


def test_sensors_have_matching_translations():
    """Verify all sensors defined in SENSORS have matching translation keys."""
    # Import SENSORS directly or parse const.py if imports fail due to HA dependency
    import re
    const_path = Path("custom_components/buienalarm/const.py")
    content = const_path.read_text(encoding="utf-8")
    sensor_keys = re.findall(r'"key":\s*"([^"]+)"', content)

    for lang in ["en", "nl"]:
        path = TRANSLATIONS_DIR / f"{lang}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        sensor_translations = data.get("entity", {}).get("sensor", {})

        for key in sensor_keys:
            assert key in sensor_translations, f"Sensor key '{key}' missing in {lang}.json entity.sensor translations"
            assert "name" in sensor_translations[key], f"Sensor key '{key}' missing 'name' in {lang}.json"
