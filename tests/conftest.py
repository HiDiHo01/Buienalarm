import sys
import os
from pathlib import Path

import pytest

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

pytest_plugins = ["pytest_homeassistant_custom_component"]

from homeassistant.const import Platform

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations automatically for all tests."""
