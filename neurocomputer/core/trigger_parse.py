import re
from typing import Dict


_INTERVAL_RE = re.compile(r"^(\d+)\s*(s|sec|seconds?|m|min|minutes?|h|hr|hours?|d|days?)$", re.I)

_UNIT_MAP = {
    "s": "seconds", "sec": "seconds", "second": "seconds", "seconds": "seconds",
    "m": "minutes", "min": "minutes", "minute": "minutes", "minutes": "minutes",
    "h": "hours", "hr": "hours", "hour": "hours", "hours": "hours",
    "d": "days", "day": "days", "days": "days",
}


def parse_interval(s: str) -> Dict[str, int]:
    """'30m' → {'minutes': 30}, '2h' → {'hours': 2}"""
    m = _INTERVAL_RE.match(s.strip())
    if not m:
        raise ValueError(f"Cannot parse interval: {s!r}. Expected formats: 30m, 2h, 1d, 45s")
    value, unit = int(m.group(1)), m.group(2).lower()
    key = _UNIT_MAP.get(unit)
    if not key:
        raise ValueError(f"Unknown interval unit: {unit!r}")
    return {key: value}


def parse_cron(s: str) -> Dict[str, str]:
    """'0 9 * * 1-5' → {minute, hour, day, month, day_of_week}"""
    parts = s.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Cron expression must have 5 fields, got {len(parts)}: {s!r}")
    keys = ["minute", "hour", "day", "month", "day_of_week"]
    return dict(zip(keys, parts))


def parse_any(s: str) -> tuple[str, dict]:
    """Return (trigger_kind, kwargs). Tries interval first, then cron."""
    try:
        return "interval", parse_interval(s)
    except ValueError:
        pass
    try:
        return "cron", parse_cron(s)
    except ValueError:
        pass
    raise ValueError(f"Cannot parse trigger: {s!r}. Use '30m', '2h', '0 9 * * 1-5', etc.")
