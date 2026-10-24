"""Test BuienalarmDataProcessor."""

from custom_components.buienalarm.processor import BuienalarmDataProcessor


def test_processor_valid_data() -> None:
    """Test data processing with valid payload."""
    raw = {
        "data": [
            {
                "precipitationrate": 1.5,
                "precipitationtype": "rain",
                "time": "2026-05-05T12:00:00Z",
            }
        ],
        "nowcastmessage": {"nl": "Regen over 5 min", "en": "Rain in 5 min"},
    }

    processor = BuienalarmDataProcessor(raw)
    result = processor.process()

    assert result["rain_expected"] is True
    assert len(result["precipitation_forecast"]) == 1
    assert result["precipitation_forecast"][0]["precipitationrate"] == 1.5
    assert result["nowcast_message"]["nl"] == "Regen over 5 min"


def test_processor_invalid_data() -> None:
    """Test data processing with invalid input."""
    processor = BuienalarmDataProcessor("invalid_string")
    result = processor.process()
    assert result == {}


def test_processor_invalid_precipitation_rates() -> None:
    """Test processor skips boolean, negative, non-finite, and malformed rates."""
    raw = {
        "data": [
            {"precipitationrate": True, "time": "2026-05-05T12:00:00Z"},
            {"precipitationrate": False, "time": "2026-05-05T12:05:00Z"},
            {"precipitationrate": -1.0, "time": "2026-05-05T12:10:00Z"},
            {"precipitationrate": float("nan"), "time": "2026-05-05T12:15:00Z"},
            {"precipitationrate": float("inf"), "time": "2026-05-05T12:20:00Z"},
            {"precipitationrate": 10**400, "time": "2026-05-05T12:25:00Z"},
            {"precipitationrate": "invalid", "time": "2026-05-05T12:30:00Z"},
            {
                "precipitationrate": "2.5",
                "precipitationtype": "rain",
                "time": "2026-05-05T12:35:00Z",
            },
        ]
    }

    processor = BuienalarmDataProcessor(raw)
    result = processor.process()

    assert result["rain_expected"] is True
    assert len(result["precipitation_forecast"]) == 1
    assert result["precipitation_forecast"][0]["precipitationrate"] == 2.5
    assert (
        result["precipitation_forecast"][0]["timestamp_utc"] == "2026-05-05T12:35:00Z"
    )


def test_processor_sample_user_data(user_sample_payload: dict) -> None:
    """Test data processing with user provided sample data payload."""
    processor = BuienalarmDataProcessor(user_sample_payload)
    result = processor.process()

    assert result["rain_expected"] is False
    assert len(result["precipitation_forecast"]) == 26
    for entry in result["precipitation_forecast"]:
        assert entry["precipitationrate"] == 0.0
        assert entry["precipitationtype"] == "rain"
    assert result["nowcast_message"]["nl"] == "Het blijft voorlopig droog"
    assert result["nowcast_message"]["en"] == "It will stay dry for now"
    assert result["nowcast_message"]["de"] == "Es bleibt vorläufig trocken"
