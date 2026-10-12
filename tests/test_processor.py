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


def test_processor_sample_user_data() -> None:
    """Test data processing with user provided sample data payload."""
    raw = {
        "data": [
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:00:00Z", "timestamp": 1791759600},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:05:00Z", "timestamp": 1791759900},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:10:00Z", "timestamp": 1791760200},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:15:00Z", "timestamp": 1791760500},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:20:00Z", "timestamp": 1791760800},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:25:00Z", "timestamp": 1791761100},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:30:00Z", "timestamp": 1791761400},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:35:00Z", "timestamp": 1791761700},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:40:00Z", "timestamp": 1791762000},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:45:00Z", "timestamp": 1791762300},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:50:00Z", "timestamp": 1791762600},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-11T23:55:00Z", "timestamp": 1791762900},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:00:00Z", "timestamp": 1791763200},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:05:00Z", "timestamp": 1791763500},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:10:00Z", "timestamp": 1791763800},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:15:00Z", "timestamp": 1791764100},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:20:00Z", "timestamp": 1791764400},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:25:00Z", "timestamp": 1791764700},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:30:00Z", "timestamp": 1791765000},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:35:00Z", "timestamp": 1791765300},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:40:00Z", "timestamp": 1791765600},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:45:00Z", "timestamp": 1791765900},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:50:00Z", "timestamp": 1791766200},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T00:55:00Z", "timestamp": 1791766500},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T01:00:00Z", "timestamp": 1791766800},
            {"lightningclass": -1, "precipitationrate": 0.0, "precipitationtype": "rain", "time": "2026-10-12T01:05:00Z", "timestamp": 1791767100},
        ],
        "daypart": [
            {"precipitationrate": 0.73, "time": "2026-10-11T22:00:00Z", "timestamp": 1791756000, "weathericon": [2, 0, -1, -1, 0, -1, -1, -1, -1]},
            {"precipitationrate": 0.0, "time": "2026-10-11T23:00:00Z", "timestamp": 1791759600, "weathericon": [0, 0, -1, -1, -1, -1, -1, -1, -1]},
            {"precipitationrate": 0.0, "time": "2026-10-12T00:00:00Z", "timestamp": 1791763200, "weathericon": [0, 0, -1, -1, -1, -1, -1, -1, -1]},
            {"precipitationrate": 0.0, "time": "2026-10-12T01:00:00Z", "timestamp": 1791766800, "weathericon": [0, 0, -1, -1, -1, -1, -1, -1, -1]},
            {"precipitationrate": 0.0, "time": "2026-10-12T02:00:00Z", "timestamp": 1791770400, "weathericon": [0, 0, -1, -1, -1, -1, -1, -1, -1]},
        ],
        "nowcastmessage": {
            "de": "Es bleibt vorläufig trocken",
            "el": "Δεν θα βρέξει προς το παρόν",
            "en": "It will stay dry for now",
            "es": "Por ahora el tiempo seguirá seco",
            "fr": "Il fera temporairement sec",
            "hr": "Za sada će ostati suho",
            "hu": "Egyelőre száraz marad az idő",
            "ispush": 0,
            "it": "Per il momento asciutto",
            "nl": "Het blijft voorlopig droog",
            "pl": "Na razie będzie sucho",
            "pt": "Vai manter-se seco por agora",
            "sv": "Uppehåll tills vidare",
            "tags": ["no precipitation"],
            "tr": "Şu an için yağış beklenmiyor",
        },
        "summary": {
            "available": True,
            "latitude": 52.787,
            "longitude": 4.798,
            "quadindex": "BCACAADDCBDABCA",
            "slice": 421490,
            "source": "radar-nl",
            "timestamp": 1791758700,
        },
    }

    processor = BuienalarmDataProcessor(raw)
    result = processor.process()

    assert result["rain_expected"] is False
    assert len(result["precipitation_forecast"]) == 26
    for entry in result["precipitation_forecast"]:
        assert entry["precipitationrate"] == 0.0
        assert entry["precipitationtype"] == "rain"
    assert result["nowcast_message"]["nl"] == "Het blijft voorlopig droog"
    assert result["nowcast_message"]["en"] == "It will stay dry for now"
    assert result["nowcast_message"]["de"] == "Es bleibt vorläufig trocken"
