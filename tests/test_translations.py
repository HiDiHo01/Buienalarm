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
