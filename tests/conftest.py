import sys
import os
import json
from pathlib import Path
from typing import Final

import pytest
from aiohttp import ClientTimeout
from unittest.mock import AsyncMock, patch

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

pytest_plugins = ["pytest_homeassistant_custom_component"]

from homeassistant.const import Platform

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations automatically for all tests."""

@pytest.fixture
def mock_buienalarm_data() -> dict:
    """Return mocked Buienalarm response data."""
    return {
        "nowcastmessage": "Regen begint over 10 minuten",
        "mycastmessage": "Droog voor de komende 30 minuten",
        "precipitationrate_now_desc": "lichte regen",
        "precipitationtype_now": "regen",
        "precipitation_duration": 12,
        "precipitationrate_now": 0.4,
        "precipitationrate_hour": 1.2,
        "precipitationrate_total": 2.3,
    }

_FIXTURE: Final[Path] = Path(__file__).parent / "mock_data" / "api_response.json"

@pytest.fixture(scope="session")
def nowcast_payload() -> dict:
    """Return the full Buienalarm JSON fixture as a dict."""
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))

@pytest.fixture(scope="session")
def expected_sensor_values(nowcast_payload) -> dict[str, object]:
    """Flatten the payload into a dict of key → expected state."""
    first_point = nowcast_payload["data"][0]       # take current sample
    return {
        "nowcastmessage": nowcast_payload["nowcastmessage"]["nl"],
        "mycastmessage":  nowcast_payload["nowcastmessage"]["nl"],
        "precipitationrate_now_desc": "Geen neerslag",
        "precipitationtype_now": first_point["precipitationtype"],
        "precipitation_duration": 0,  # you might compute duration yourself
        "precipitationrate_now": first_point["precipitationrate"],
        "precipitationrate_hour": 0.0,   # if your code calculates an hour‑sum
        "precipitationrate_total": 0.0,  # ditto
    }
