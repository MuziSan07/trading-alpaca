"""
Live WebSocket price streaming (Alpaca StockDataStream).

Replaces constant REST polling: subscribes to live trades and keeps the latest
price in memory. Runs in a background thread so the executor can read prices
without blocking. Falls back gracefully — if the stream can't start, the
executor still works via REST snapshots.
"""
from __future__ import annotations

import threading

from alpaca.data.live import StockDataStream
from alpaca.data.enums import DataFeed

from .config import CONFIG
from .logger import get_logger

log = get_logger("stream")


class PriceStream:
    def __init__(self) -> None:
        feed = DataFeed.SIP if CONFIG.data_feed.lower() == "sip" else DataFeed.IEX
        self._stream = StockDataStream(
            CONFIG.alpaca_api_key, CONFIG.alpaca_secret_key, feed=feed
        )
        self._prices: dict[str, float] = {}
        self._thread: threading.Thread | None = None
        self._running = False

    async def _on_trade(self, trade) -> None:
        self._prices[trade.symbol] = float(trade.price)

    def start(self, symbol: str) -> bool:
        try:
            self._stream.subscribe_trades(self._on_trade, symbol)
            self._thread = threading.Thread(target=self._stream.run, daemon=True)
            self._thread.start()
            self._running = True
            log.info("WebSocket stream started for %s", symbol)
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("Stream failed to start (%s) — will fall back to polling", e)
            return False

    def get(self, symbol: str) -> float | None:
        return self._prices.get(symbol)

    def stop(self) -> None:
        if self._running:
            try:
                self._stream.stop()
            except Exception:  # noqa: BLE001
                pass
            self._running = False
            log.info("WebSocket stream stopped")
