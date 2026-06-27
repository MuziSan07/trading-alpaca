"""
Free fundamentals via yfinance (open-source Yahoo Finance).

Used for data Alpaca does NOT provide for free:
  - share FLOAT  -> powers the low-float filter
  - full-market VOLUME cross-check (Alpaca's free IEX feed is partial)

Everything degrades gracefully: if yfinance is unavailable or a field is
missing, the bot logs it and does NOT block the trade on that single filter.
"""
from __future__ import annotations

from functools import lru_cache

from .logger import get_logger

log = get_logger("fundamentals")

try:
    import yfinance as yf
    _AVAILABLE = True
except ImportError:  # keep the bot runnable even if yfinance isn't installed
    _AVAILABLE = False
    log.warning("yfinance not installed — float/volume enrichment disabled")


@lru_cache(maxsize=512)
def get_float(symbol: str) -> int | None:
    """Free float (shares available to trade). None if unknown."""
    if not _AVAILABLE:
        return None
    try:
        info = yf.Ticker(symbol).info
        f = info.get("floatShares") or info.get("sharesOutstanding")
        return int(f) if f else None
    except Exception as e:  # noqa: BLE001
        log.warning("Float lookup failed for %s: %s", symbol, e)
        return None


@lru_cache(maxsize=512)
def get_full_volume(symbol: str) -> int | None:
    """Full-market daily volume (more accurate than free IEX). None if unknown."""
    if not _AVAILABLE:
        return None
    try:
        info = yf.Ticker(symbol).info
        v = info.get("volume") or info.get("regularMarketVolume")
        return int(v) if v else None
    except Exception as e:  # noqa: BLE001
        log.warning("Volume lookup failed for %s: %s", symbol, e)
        return None


def is_low_float(symbol: str, max_float: int) -> bool:
    """True if float is known AND <= max_float. Unknown float -> do not block."""
    f = get_float(symbol)
    if f is None:
        return True  # data missing: don't reject on this single filter
    low = f <= max_float
    log.info("%s float=%s (<= %s ? %s)", symbol, f, max_float, low)
    return low
