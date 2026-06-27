"""
Order execution + exit management.

Entry: limit buy (premarket-compatible). We read the ACTUAL filled quantity
(handles partial fills) and split the exits off that real number:
  - 75% at +5%
  - 25% at +7%
  - whole remaining position exited at -3%

Premarket-safe: ALL exits (including the stop) use LIMIT orders, because Alpaca
rejects market orders outside regular hours. The stop sells with an aggressive
limit (just below the live price) so it still fills quickly.

Fill-aware: a resting take-profit is verified as filled before we treat that
slice as sold, and any resting order is cancelled before a stop exit so we never
double-sell or skip an unfilled leg.
"""
from __future__ import annotations

import time

from alpaca.trading.enums import OrderStatus

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
        if self.stream:
            p = self.stream.get(symbol)
            if p:
                return p
        snap = market.snapshots([symbol]).get(symbol)
        if snap and snap.latest_trade:
            return float(snap.latest_trade.price)
        if snap and snap.daily_bar:
            return float(snap.daily_bar.close)
        return None

    def _limit_sell(self, symbol: str, qty: int, limit_price: float):
        """Premarket-safe sell (limit order)."""
        if qty <= 0:
            return None
        return self.broker.submit_limit_sell(symbol, qty, limit_price)

    def _aggressive_exit(self, symbol: str, qty: int, ref_price: float):
        """Sell now via a limit priced just below market so it crosses and fills."""
        return self._limit_sell(symbol, qty, ref_price * 0.99)

    def _is_filled(self, order_id) -> bool:
        try:
            return self.broker.get_order(order_id).status == OrderStatus.FILLED
        except Exception:  # noqa: BLE001
            return False

    def enter(self, plan: TradePlan) -> float:
        """Submit entry, wait for fill, return ACTUAL filled qty."""
        order = self.broker.submit_limit_buy(plan.symbol, plan.qty, plan.entry * 1.005)
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
        tp2_qty = filled - tp1_qty
        remaining = filled
        tp1_order = None
        tp1_filled = False

        if self.stream:
            self.stream.start(plan.symbol)

        deadline = time.time() + max_minutes * 60
        try:
            while time.time() < deadline:
                price = self._current_price(plan.symbol, market)
                if price is None:
                    time.sleep(poll_secs)
                    continue

                # Reconcile a resting TP1 before any other decision
                if tp1_order is not None and not tp1_filled:
                    if self._is_filled(tp1_order):
                        tp1_filled = True
                        remaining -= tp1_qty
                        log.info("TP1 confirmed filled on %s (%d left)", plan.symbol, remaining)

                # Stop loss — cancel any resting TP, then exit everything (limit)
                if price <= plan.stop_price:
                    log.warning("STOP hit on %s @ $%.2f — exiting %d", plan.symbol, price, remaining)
                    if tp1_order is not None and not tp1_filled:
                        self.broker.cancel_order(tp1_order)
                    self._aggressive_exit(plan.symbol, remaining, price)
                    return "stopped"

                # TP1: place the 75% limit sell once
                if tp1_order is None and price >= plan.tp1_price:
                    log.info("TP1 hit %s @ $%.2f — sell %d @ $%.2f",
                             plan.symbol, price, tp1_qty, plan.tp1_price)
                    o = self._limit_sell(plan.symbol, tp1_qty, plan.tp1_price)
                    tp1_order = o.id if o else None

                # TP2: only after TP1 actually filled
                if tp1_filled and price >= plan.tp2_price:
                    log.info("TP2 hit %s @ $%.2f — sell %d @ $%.2f",
                             plan.symbol, price, remaining, plan.tp2_price)
                    o = self._limit_sell(plan.symbol, remaining, plan.tp2_price)
                    if o:
                        self.broker.wait_for_fill(o.id, timeout=60)
                    return "target_reached"

                time.sleep(poll_secs)

            # End of session — cancel resting orders, flatten what's left
            log.info("End of session — flattening remaining %s", plan.symbol)
            if tp1_order is not None and not tp1_filled:
                self.broker.cancel_order(tp1_order)
            last = self._current_price(plan.symbol, market) or plan.entry
            self._aggressive_exit(plan.symbol, remaining, last)
            return "eod_close"
        finally:
            if self.stream:
                self.stream.stop()
