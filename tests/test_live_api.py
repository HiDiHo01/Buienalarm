"""Opt-in live smoke test for the Buienalarm API and period parsing."""

import os
from collections.abc import Mapping

import aiohttp
import pytest
from homeassistant.core import HomeAssistant

from custom_components.buienalarm.api import BuienalarmApiClient
from custom_components.buienalarm.binary_sensor import (
    _as_float,
    _get_precipitation_periods,
    _is_precipitation_period,
)

pytestmark = pytest.mark.skipif(
    os.getenv("BUIENALARM_LIVE_TEST") != "1",
    reason="Set BUIENALARM_LIVE_TEST=1 to run against the live Buienalarm API",
)


@pytest.mark.asyncio
async def test_live_api_payload_matches_integration_expectations(
    hass: HomeAssistant,
) -> None:
    """Fetch live data and validate the fields consumed by the integration."""
    latitude = float(os.getenv("BUIENALARM_TEST_LATITUDE", "52.3676"))
    longitude = float(os.getenv("BUIENALARM_TEST_LONGITUDE", "4.9041"))

    # pytest-asyncio's test loop may differ from hass.loop. Use a session
    # owned by the active test loop so aiohttp's connector and DNS resolver
    # are never used from a different event loop. Production setup continues
    # to use Home Assistant's shared session.
    async with aiohttp.ClientSession() as session:
        client = BuienalarmApiClient(latitude, longitude, session, hass)
        result = await client.async_get_data()

    assert isinstance(result, Mapping), "API client did not return a mapping"
    timeseries = result.get("timeseries")
    assert isinstance(timeseries, Mapping), "Live response has no timeseries mapping"

    periods = _get_precipitation_periods(timeseries)
    assert periods, "Live response contains no usable precipitation periods"

    valid_periods = [
        period
        for period in periods
        if _as_float(period.get("timestamp")) is not None
        and _as_float(period.get("precipitationrate")) is not None
    ]
    assert valid_periods, (
        "No live precipitation period contains numeric timestamp and "
        "precipitationrate fields"
    )

    # Exercise the same classification function used by the binary sensors.
    for period in valid_periods:
        assert isinstance(_is_precipitation_period(period), bool)

    retrieval_time = result.get("retrieval_time")
    assert retrieval_time is not None and retrieval_time.tzinfo is not None
    assert isinstance(result.get("cache_age"), int)
