import json
from unittest.mock import patch
import datetime
import pytest
from handler import handler, get_events_for_date


def test_valborg_on_april_30():
    date = datetime.date(2026, 4, 30)
    events = get_events_for_date(date)
    assert "Valborg" in events


def test_christmas_on_dec_25():
    date = datetime.date(2026, 12, 25)
    events = get_events_for_date(date)
    assert "Christmas" in events


def test_no_events_on_ordinary_day():
    # Pick a date unlikely to have events — adjust if you add one for this date
    date = datetime.date(2026, 3, 3)
    events = get_events_for_date(date)
    assert events == []


def test_handler_returns_date_and_events():
    fixed_date = datetime.date(2026, 4, 30)
    with patch("handler.get_today", return_value=fixed_date):
        result = handler({}, {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["date"] == "2026-04-30"
    assert "Valborg" in body["events"]


def test_cors_header_present():
    result = handler({}, {})
    assert result["headers"]["Access-Control-Allow-Origin"] == "*"
