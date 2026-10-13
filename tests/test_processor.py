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
