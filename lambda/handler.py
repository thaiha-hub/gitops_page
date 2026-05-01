import json
import datetime


EVENTS = {
    "01-01": ["New Year's Day"],
    "01-13": ["Tjugondag Knut"],
    "02-14": ["Valentine's Day"],
    "04-22": ["Earth Day"],
    "04-30": ["Valborg"],
    "05-01": ["International Workers' Day"],
    "06-05": ["World Environment Day"],
    "06-06": ["Swedish National Day"],
    "10-31": ["Halloween"],
    "11-11": ["Singles' Day", "Armistice Day"],
    "12-10": ["Nobel Day"],
    "12-13": ["Lucia"],
    "12-24": ["Christmas Eve"],
    "12-25": ["Christmas"],
    "12-31": ["New Year's Eve"],
}


def get_today():
    return datetime.datetime.now(datetime.timezone.utc).date()


def get_events_for_date(date):
    key = date.strftime("%m-%d")
    return EVENTS.get(key, [])


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
