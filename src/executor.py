"""
Order execution + exit management.

Entry: limit buy (premarket-compatible). We then read the ACTUAL filled
quantity (handles partial fills) and split the exits off that real number:
  - 75% at +5%
  - 25% at +7%
  - whole remaining position stopped out at -3%

Price source: live WebSocket stream when available, REST snapshot as fallback.
Two take-profit levels mean a single native bracket order can't express this
(Alpaca brackets allow only one TP leg), so exits are managed here against the
live price — sized from the real fill.
"""
from __future__ import annotations

import time

from .broker import Broker
from .config import CONFIG
from .logger import get_logger
from .risk_manager import TradePlan
from . import state

log = get_logger("executor")


class Executor:
    def __init__(self, broker: Broker, stream=None) -> None:
        self.broker = broker
        self.stream = stream  # optional PriceStream

    def _current_price(self, symbol: str, market) -> float | None:
        # 1) live websocket price
        if self.stream:
            p = self.stream.get(symbol)
            if p:
                return p
        # 2) fallback: REST snapshot
        snap = market.snapshots([symbol]).get(symbol)
        if snap and snap.latest_trade:
            return float(snap.latest_trade.price)
        if snap and snap.daily_bar:
            return float(snap.daily_bar.close)
        return None

    def enter(self, plan: TradePlan) -> float:
        """Submit entry, wait for fill, return ACTUAL filled qty."""
        order = self.broker.submit_limit_buy(
            plan.symbol, plan.qty, plan.entry * 1.005  # small buffer to fill
        )
        state.record_trade(plan.symbol)
        filled = self.broker.wait_for_fill(order.id)
        if filled <= 0:
            log.warning("Entry on %s did not fill — no position to manage", plan.symbol)
        else:
            log.info("Entered %s — filled %.0f / %d shares", plan.symbol, filled, plan.qty)
        return filled

    def manage(self, plan: TradePlan, market, filled_qty: float,
               poll_secs: int = 5, max_minutes: int = 390) -> str:
        """Manage scale-out exits, sized from the ACTUAL filled quantity."""
        filled = int(filled_qty)
        if filled <= 0:
            return "no_fill"

        tp1_qty = int(filled * CONFIG.tp1_size)
        tp2_qty = filled - tp1_qty  # remainder so nothing is left stranded
        tp1_done = False

        if self.stream:
            self.stream.start(plan.symbol)

        deadline = time.time() + max_minutes * 60
        try:
            while time.time() < deadline:
                price = self._current_price(plan.symbol, market)
                if price is None:
                    time.sleep(poll_secs)
                    continue

                # Stop loss — exit everything
                if price <= plan.stop_price:
                    log.warning("STOP hit on %s @ $%.2f — closing", plan.symbol, price)
                    self.broker.close_position(plan.symbol)
                    return "stopped"

                # TP1: sell 75%
                if not tp1_done and price >= plan.tp1_price:
                    log.info("TP1 hit %s @ $%.2f — sell %d", plan.symbol, price, tp1_qty)
                    self.broker.submit_limit_sell(plan.symbol, tp1_qty, plan.tp1_price)
                    tp1_done = True

                # TP2: sell remaining 25%
                if tp1_done and price >= plan.tp2_price:
                    log.info("TP2 hit %s @ $%.2f — sell %d", plan.symbol, price, tp2_qty)
                    self.broker.submit_limit_sell(plan.symbol, tp2_qty, plan.tp2_price)
                    return "target_reached"

                time.sleep(poll_secs)

            # End of session — close whatever is left
            log.info("End of session — closing remaining %s", plan.symbol)
            try:
                self.broker.close_position(plan.symbol)
            except Exception as e:  # noqa: BLE001
                log.info("No open position to close for %s (%s)", plan.symbol, e)
            return "eod_close"
        finally:
            if self.stream:
                self.stream.stop()
