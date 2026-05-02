import json
import datetime
import urllib.request

_cache = {}


def _fetch_year(year):
    base = "https://api.dagsmart.se"

    def fetch(path):
        url = f"{base}/{path}?year={year}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read())

    index = {}
    for item in fetch("holidays"):
        index.setdefault(item["date"], []).append(item["name"]["en"])
    for item in fetch("half-days"):
        index.setdefault(item["date"], []).append("Half-day (halvdag)")
    for item in fetch("bridge-days"):
        index.setdefault(item["date"], []).append("Bridge day (klämdag)")

    return index


def _get_events_index(year):
    if year not in _cache:
        _cache[year] = _fetch_year(year)
    return _cache[year]


def get_today():
    return datetime.datetime.now(datetime.timezone.utc).date()


def get_events_for_date(date):
    index = _get_events_index(date.year)
    return index.get(date.isoformat(), [])


def handler(event, context):
    today = get_today()
    events = get_events_for_date(today)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps({
            "date": today.isoformat(),
            "events": events,
        }),
    }
