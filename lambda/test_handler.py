import json
from unittest.mock import patch, MagicMock
import datetime
import pytest
from handler import handler, get_events_for_date, _fetch_year

MOCK_INDEX = {
    "2026-01-01": ["New Year's Day"],
    "2026-04-03": ["Good Friday"],
    "2026-04-30": ["Half-day (halvdag)"],
    "2026-05-22": ["Bridge day (klämdag)"],
}


def test_holiday_on_known_date():
    with patch("handler._get_events_index", return_value=MOCK_INDEX):
        assert "New Year's Day" in get_events_for_date(datetime.date(2026, 1, 1))


def test_half_day_on_known_date():
    with patch("handler._get_events_index", return_value=MOCK_INDEX):
        assert "Half-day (halvdag)" in get_events_for_date(datetime.date(2026, 4, 30))


def test_bridge_day_on_known_date():
    with patch("handler._get_events_index", return_value=MOCK_INDEX):
        assert "Bridge day (klämdag)" in get_events_for_date(datetime.date(2026, 5, 22))


def test_no_events_on_ordinary_day():
    with patch("handler._get_events_index", return_value=MOCK_INDEX):
        assert get_events_for_date(datetime.date(2026, 3, 3)) == []


def test_handler_returns_date_and_events():
    fixed_date = datetime.date(2026, 1, 1)
    with patch("handler.get_today", return_value=fixed_date), \
         patch("handler._get_events_index", return_value=MOCK_INDEX):
        result = handler({}, {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["date"] == "2026-01-01"
    assert "New Year's Day" in body["events"]


def test_cors_header_present():
    with patch("handler._get_events_index", return_value={}):
        result = handler({}, {})
    assert result["headers"]["Access-Control-Allow-Origin"] == "*"


def test_cache_used_for_same_year(monkeypatch):
    monkeypatch.setattr("handler._cache", {})
    call_count = {"n": 0}

    def mock_fetch(year):
        call_count["n"] += 1
        return {}

    monkeypatch.setattr("handler._fetch_year", mock_fetch)
    get_events_for_date(datetime.date(2026, 1, 1))
    get_events_for_date(datetime.date(2026, 6, 15))
    assert call_count["n"] == 1


def _make_urlopen_mock(holidays, half_days, bridge_days):
    responses = [
        json.dumps(holidays).encode(),
        json.dumps(half_days).encode(),
        json.dumps(bridge_days).encode(),
    ]
    calls = {"i": 0}

    def mock_urlopen(url, timeout=None):
        m = MagicMock()
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        m.read.return_value = responses[calls["i"]]
        calls["i"] += 1
        return m

    return mock_urlopen


def test_fetch_year_parses_holidays():
    mock = _make_urlopen_mock(
        holidays=[{"date": "2026-01-01", "code": "newYearsDay", "name": {"en": "New Year's Day", "sv": "nyårsdagen"}}],
        half_days=[],
        bridge_days=[],
    )
    with patch("urllib.request.urlopen", side_effect=mock):
        index = _fetch_year(2026)
    assert "New Year's Day" in index["2026-01-01"]


def test_fetch_year_parses_half_and_bridge_days():
    mock = _make_urlopen_mock(
        holidays=[],
        half_days=[{"date": "2026-04-30"}],
        bridge_days=[{"date": "2026-05-22"}],
    )
    with patch("urllib.request.urlopen", side_effect=mock):
        index = _fetch_year(2026)
    assert "Half-day (halvdag)" in index["2026-04-30"]
    assert "Bridge day (klämdag)" in index["2026-05-22"]
