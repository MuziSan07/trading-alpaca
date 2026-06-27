"""
The Scanner — applies the client's hard numeric filters to find candidates.

Filters (from the client's strategy):
  1. price <= $5.00
  2. volume >= 1,000,000
  3. price move >= +$0.20 today
  4. volume increasing
  5. price increasing
  6. historical pop >= $0.50 (a past day moved at least $0.50)
  7. low float (see note — needs an external float data source)

Selection rule: among all candidates, pick the HIGHEST volume one.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import CONFIG
from .fundamentals import is_low_float
from .logger import get_logger
from .market_data import MarketData

log = get_logger("scanner")


@dataclass
class Candidate:
    symbol: str
    price: float
    volume: float
    move: float            # today's $ change
    pct_change: float
    popped_before: bool
    max_past_pop: float


class Scanner:
    def __init__(self, market: MarketData) -> None:
        self.market = market

    def _popped_before(self, symbol: str) -> tuple[bool, float]:
        """Did this stock move >= HISTORICAL_POP ($0.50) on any past day?"""
        bars = self.market.daily_bars(symbol)
        max_pop = 0.0
        for b in bars:
            pop = float(b.high) - float(b.low)
            max_pop = max(max_pop, pop)
        return max_pop >= CONFIG.historical_pop, max_pop

    def scan(self) -> list[Candidate]:
        symbols = self.market.most_active_symbols(top=100)
        log.info("Scanning %d most-active symbols", len(symbols))
        snaps = self.market.snapshots(symbols)

        candidates: list[Candidate] = []
        for sym in symbols:
            snap = snaps.get(sym)
            if snap is None or snap.daily_bar is None:
                continue

            bar = snap.daily_bar
            prev = snap.previous_daily_bar
            price = float(bar.close)
            volume = float(bar.volume)

            # Filter 1: penny stock within $1–$5 (floor avoids illiquid sub-$1)
            if price > CONFIG.max_price or price < CONFIG.min_price:
                continue
            # Filter 2: high volume
            if volume < CONFIG.min_volume:
                continue

            prev_close = float(prev.close) if prev else float(bar.open)
            move = price - prev_close
            pct = (move / prev_close) if prev_close else 0.0

            # Filter 3: moved up >= $0.20
            if move < CONFIG.min_price_move:
                continue
            # Filter 5: price increasing (close above open)
            if price < float(bar.open):
                continue
            # Filter 4: volume increasing vs prior day
            if prev and volume < float(prev.volume):
                continue

            # Filter 6: popped >= $0.50 in the past
            popped, max_pop = self._popped_before(sym)
            if not popped:
                continue

            # Filter 7: low float (free data via yfinance)
            if not is_low_float(sym, CONFIG.max_float):
                log.info("skip %s — float above %s", sym, CONFIG.max_float)
                continue

            candidates.append(
                Candidate(sym, price, volume, move, pct, popped, max_pop)
            )
            log.info(
                "PASS %s | $%.2f | vol %.0f | move +$%.2f (%.1f%%) | past pop $%.2f",
                sym, price, volume, move, pct * 100, max_pop,
            )

        # Selection rule: HIGHEST volume wins
        candidates.sort(key=lambda c: c.volume, reverse=True)
        return candidates
