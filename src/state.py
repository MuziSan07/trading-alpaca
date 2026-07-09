"""
Persisted daily state so a restart never double-trades.
Tracks how many trades were taken today (enforces one-trade-per-day).
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from .logger import get_logger

log = get_logger("state")
STATE_DIR = "state"
STATE_FILE = os.path.join(STATE_DIR, "daily_state.json")
_ET = ZoneInfo("America/New_York")


def _today() -> str:
    """Trading day keyed to US/Eastern (market) time, not the server clock.
    This is why 'trades today' resets correctly at ET midnight regardless of
    where the bot runs."""
    return datetime.now(_ET).date().isoformat()


def _load() -> dict:
    os.makedirs(STATE_DIR, exist_ok=True)
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def trades_today() -> int:
    data = _load()
    if data.get("date") != _today():
        return 0
    return int(data.get("count", 0))


def record_trade(symbol: str) -> None:
    data = _load()
    if data.get("date") != _today():
        data = {"date": _today(), "count": 0, "symbols": []}
    data["count"] = int(data.get("count", 0)) + 1
    data.setdefault("symbols", []).append(symbol)
    _save(data)
    log.info("Recorded trade #%d today: %s", data["count"], symbol)
