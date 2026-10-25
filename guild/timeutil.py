"""UTC storage, Central display. No full timezone handling (phase 1)."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

FMT = "%Y-%m-%d %H:%M:%S"
CENTRAL = ZoneInfo("America/Chicago")


def now_str():
    return datetime.now(timezone.utc).strftime(FMT)


def parse(ts):
    return datetime.strptime(ts, FMT).replace(tzinfo=timezone.utc)


def to_central(ts, fmt="%b %-d, %-I:%M %p %Z"):
    return parse(ts).astimezone(CENTRAL).strftime(fmt) if ts else ""


def days_since(ts):
    return (datetime.now(timezone.utc) - parse(ts)).days


def central_input_to_utc(value):
    """Convert a <input type=datetime-local> value (Central) to a UTC string."""
    local = datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(tzinfo=CENTRAL)
    return local.astimezone(timezone.utc).strftime(FMT)
