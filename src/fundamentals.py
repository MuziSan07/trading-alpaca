"""
Free fundamentals via yfinance (open-source Yahoo Finance).

Used for data Alpaca does NOT provide for free:
  - share FLOAT  -> powers the low-float filter
  - full-market VOLUME cross-check (Alpaca's free IEX feed is partial)

Throttle-safe: results are cached to disk for 24h (float changes slowly), with
a short retry/backoff and a tiny inter-call delay so scanning many symbols does
not hammer Yahoo and get rate-limited. Everything degrades gracefully: if a
field is missing or yfinance is unavailable, the bot logs it and does NOT block
the trade on that single filter.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date

from .logger import get_logger

log = get_logger("fundamentals")

try:
    import yfinance as yf
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False
    log.warning("yfinance not installed — float/volume enrichment disabled")

_CACHE_DIR = "state"
_CACHE_FILE = os.path.join(_CACHE_DIR, "fundamentals_cache.json")
_RETRIES = 2
_BACKOFF = 1.5      # seconds, grows per retry
_CALL_DELAY = 0.3   # polite delay between live lookups
_mem: dict | None = None


def _load_cache() -> dict:
    global _mem
    if _mem is not None:
        return _mem
    if os.path.exists(_CACHE_FILE):
        try:
            _mem = json.load(open(_CACHE_FILE))
        except Exception:  # noqa: BLE001
            _mem = {}
    else:
        _mem = {}
    return _mem


def _save_cache() -> None:
    if _mem is None:
        return
    os.makedirs(_CACHE_DIR, exist_ok=True)
    try:
        json.dump(_mem, open(_CACHE_FILE, "w"))
    except Exception:  # noqa: BLE001
        pass


def _cached(symbol: str) -> dict | None:
    entry = _load_cache().get(symbol)
    if entry and entry.get("date") == date.today().isoformat():
        return entry
    return None


def _fetch_info(symbol: str) -> dict:
    """Fetch with retry/backoff; cache the result for the day."""
    cached = _cached(symbol)
    if cached is not None:
        return cached
    if not _AVAILABLE:
        return {}

    info = {}
    for attempt in range(_RETRIES + 1):
        try:
            raw = yf.Ticker(symbol).info
            info = {
                "float": raw.get("floatShares") or raw.get("sharesOutstanding"),
                "volume": raw.get("volume") or raw.get("regularMarketVolume"),
            }
            break
        except Exception as e:  # noqa: BLE001
            if attempt < _RETRIES:
                time.sleep(_BACKOFF * (attempt + 1))
            else:
                log.warning("Fundamentals fetch failed for %s: %s", symbol, e)
                info = {}
    info["date"] = date.today().isoformat()
    _load_cache()[symbol] = info
    _save_cache()
    time.sleep(_CALL_DELAY)
    return info


def get_float(symbol: str) -> int | None:
    f = _fetch_info(symbol).get("float")
    return int(f) if f else None


def get_full_volume(symbol: str) -> int | None:
    v = _fetch_info(symbol).get("volume")
    return int(v) if v else None


def is_low_float(symbol: str, max_float: int) -> bool:
    """True if float is known AND <= max_float. Unknown float -> do not block."""
    f = get_float(symbol)
    if f is None:
        return True  # data missing: don't reject on this single filter
    low = f <= max_float
    log.info("%s float=%s (<= %s ? %s)", symbol, f, max_float, low)
    return low
