"""
Market data layer: builds the candidate universe (most-active stocks) and
fetches snapshots + historical bars needed by the scanner and AI.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.screener import ScreenerClient
from alpaca.data.requests import (
    MostActivesRequest,
    StockSnapshotRequest,
    StockBarsRequest,
)
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

from .config import CONFIG
from .logger import get_logger

log = get_logger("market_data")


class MarketData:
    def __init__(self) -> None:
        self.hist = StockHistoricalDataClient(
            CONFIG.alpaca_api_key, CONFIG.alpaca_secret_key
        )
        self.screener = ScreenerClient(
            CONFIG.alpaca_api_key, CONFIG.alpaca_secret_key
        )
        self.feed = DataFeed.SIP if CONFIG.data_feed.lower() == "sip" else DataFeed.IEX

    def most_active_symbols(self, top: int = 100) -> list[str]:
        """Top traded stocks by volume — our raw candidate pool."""
        try:
            actives = self.screener.get_most_actives(
                MostActivesRequest(top=top)
            )
            return [a.symbol for a in actives.most_actives]
        except Exception as e:  # noqa: BLE001
            log.error("Most-actives fetch failed: %s", e)
            return []

    def snapshots(self, symbols: list[str]) -> dict:
        """Latest snapshot (price, daily bar, prev close) per symbol."""
        if not symbols:
            return {}
        try:
            req = StockSnapshotRequest(symbol_or_symbols=symbols, feed=self.feed)
            return self.hist.get_stock_snapshots(req)
        except Exception as e:  # noqa: BLE001
            log.error("Snapshot fetch failed: %s", e)
            return {}

    def intraday_bars(self, symbol: str, minutes: int = 180):
        """Recent minute bars for the intraday price chart."""
        try:
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=datetime.now() - timedelta(minutes=minutes),
                feed=self.feed,
            )
            bars = self.hist.get_stock_bars(req)
            return bars.data.get(symbol, [])
        except Exception as e:  # noqa: BLE001
            log.error("Intraday bars fetch failed for %s: %s", symbol, e)
            return []

    def daily_bars(self, symbol: str, days: int = 30):
        """Historical daily bars — used for the 'popped $0.50+ before' check."""
        try:
            req = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=days),
                feed=self.feed,
            )
            bars = self.hist.get_stock_bars(req)
            return bars.data.get(symbol, [])
        except Exception as e:  # noqa: BLE001
            log.error("Daily bars fetch failed for %s: %s", symbol, e)
            return []
