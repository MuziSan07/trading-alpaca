"""
Live WebSocket price streaming (Alpaca StockDataStream) with auto-reconnect.

Keeps the latest trade price in memory. Runs in a supervised background thread:
if the socket drops ("no close frame received", timeouts, etc.) it reconnects
with capped exponential backoff instead of crashing the bot. Falls back to REST
snapshots in the executor whenever a live price isn't available.
"""
from __future__ import annotations

import threading
import time

from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed

from .config import CONFIG
from .logger import get_logger

log = get_logger("stream")


class PriceStream:
    def __init__(self) -> None:
        self._feed = DataFeed.SIP if CONFIG.data_feed.lower() == "sip" else DataFeed.IEX
        self._prices: dict[str, float] = {}
        self._symbol: str | None = None
        self._stream = None
        self._thread: threading.Thread | None = None
        self._stop = False
        self.last_update = 0.0

    async def _on_trade(self, trade) -> None:
        self._prices[trade.symbol] = float(trade.price)
        self.last_update = time.time()

    def _make_stream(self):
        s = StockDataStream(CONFIG.alpaca_api_key, CONFIG.alpaca_secret_key, feed=self._feed)
        s.subscribe_trades(self._on_trade, self._symbol)
        return s

    def _supervise(self) -> None:
        backoff = 1
        while not self._stop:
            try:
                self._stream = self._make_stream()
                log.info("WebSocket connecting for %s", self._symbol)
                self._stream.run()  # blocks until the socket errors or stop()
                backoff = 1
            except Exception as e:  # noqa: BLE001
                if self._stop:
                    break
                log.warning("WebSocket dropped (%s) — reconnecting in %ss", e, backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
        log.info("WebSocket supervisor stopped")

    def start(self, symbol: str) -> bool:
        self._symbol = symbol
        self._stop = False
        self._thread = threading.Thread(target=self._supervise, daemon=True)
        self._thread.start()
        return True

    def get(self, symbol: str) -> float | None:
        return self._prices.get(symbol)

    def is_stale(self, max_age: float = 120.0) -> bool:
        """True if we've never received data or it's older than max_age seconds."""
        return self.last_update == 0.0 or (time.time() - self.last_update) > max_age

    def stop(self) -> None:
        self._stop = True
        try:
            if self._stream:
                self._stream.stop()
        except Exception:  # noqa: BLE001
            pass
