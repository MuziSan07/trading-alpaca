"""
Order execution + exit management.

Entry: limit buy (premarket-compatible). We read the ACTUAL filled quantity
(handles partial fills) and split the exits off that real number:
  - 75% at +TP1
  - 25% at +TP2
  - whole remaining position exited at the stop

Premarket-safe: ALL exits (including the stop) use LIMIT orders, because Alpaca
rejects market orders outside regular hours. The stop sells with an aggressive
limit (just below the live price) so it still fills quickly.

Fill-aware: a resting take-profit is verified filled before that slice counts as
sold, and any resting order is cancelled before a stop exit.

EOD: positions are force-closed at a FIXED wall-clock time (EOD_CLOSE, default
20:00 America/New_York) — not a relative timer that depended on entry time.

Recovery: manage() accepts recovered=True to resume protecting a position found
open at startup (single protective stop + take-profit on the remaining shares).
"""
from __future__ import annotations

import time
from datetime import datetime
from zoneinfo import ZoneInfo

from alpaca.trading.enums import OrderStatus

from .broker import Broker
from .config import CONFIG
from .logger import get_logger
from .risk_manager import TradePlan
from . import state

log = get_logger("executor")
_ET = ZoneInfo("America/New_York")


def _eod_deadline_epoch() -> float:
    """Epoch seconds for today's EOD_CLOSE in ET (or now, if already past)."""
    try:
        hh, mm = (int(x) for x in CONFIG.eod_close.split(":"))
    except Exception:  # noqa: BLE001
        hh, mm = 20, 0
    now = datetime.now(_ET)
    cutoff = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return cutoff.timestamp() if now < cutoff else time.time()


class Executor:
    def __init__(self, broker: Broker, stream=None) -> None:
        self.broker = broker
        self.stream = stream  # optional PriceStream

    def _current_price(self, symbol: str, market) -> float | None:
        if self.stream:
            p = self.stream.get(symbol)
            if p:
                return p
        if market is None:
            return None
        snap = market.snapshots([symbol]).get(symbol)
        if snap and snap.latest_trade:
            return float(snap.latest_trade.price)
        if snap and snap.daily_bar:
            return float(snap.daily_bar.close)
        return None

    def _limit_sell(self, symbol: str, qty: int, limit_price: float):
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
        order = self.broker.submit_limit_buy(plan.symbol, plan.qty, plan.entry * 1.005)
        state.record_trade(plan.symbol)
        filled = self.broker.wait_for_fill(order.id)
        if filled <= 0:
            log.warning("Entry on %s did not fill — no position to manage", plan.symbol)
        else:
            log.info("Entered %s — filled %.0f / %d shares", plan.symbol, filled, plan.qty)
        return filled

    def manage(self, plan: TradePlan, market, filled_qty: float,
               poll_secs: int = 5, recovered: bool = False,
               deadline: float | None = None) -> str:
        """Manage scale-out exits until closed or the fixed EOD cutoff.
        recovered=True: skip the TP1 scale (we can't know if it already sold) and
        simply protect the remaining shares with a stop + single take-profit."""
        filled = int(filled_qty)
        if filled <= 0:
            return "no_fill"

        if recovered:
            tp1_qty, tp2_qty, tp1_done = 0, filled, True
            log.info("RECOVERY: protecting %d %s (stop $%.2f / TP $%.2f)",
                     filled, plan.symbol, plan.stop_price, plan.tp2_price)
        else:
            tp1_qty = int(filled * CONFIG.tp1_size)
            tp2_qty = filled - tp1_qty
            tp1_done = False
        remaining = filled
        tp1_order = None

        if self.stream:
            self.stream.start(plan.symbol)

        if deadline is None:
            deadline = _eod_deadline_epoch()
        try:
            while time.time() < deadline:
                price = self._current_price(plan.symbol, market)
                if price is None:
                    time.sleep(poll_secs)
                    continue

                if tp1_order is not None and not tp1_done:
                    if self._is_filled(tp1_order):
                        tp1_done = True
                        remaining -= tp1_qty
                        log.info("TP1 confirmed filled on %s (%d left)", plan.symbol, remaining)

                # Stop loss — cancel resting TP, then exit everything (limit)
                if price <= plan.stop_price:
                    log.warning("STOP hit on %s @ $%.2f — exiting %d", plan.symbol, price, remaining)
                    if tp1_order is not None and not tp1_done:
                        self.broker.cancel_order(tp1_order)
                    self._aggressive_exit(plan.symbol, remaining, price)
                    return "stopped"

                if not recovered and tp1_order is None and price >= plan.tp1_price:
                    log.info("TP1 hit %s @ $%.2f — sell %d @ $%.2f",
                             plan.symbol, price, tp1_qty, plan.tp1_price)
                    o = self._limit_sell(plan.symbol, tp1_qty, plan.tp1_price)
                    tp1_order = o.id if o else None

                if tp1_done and price >= plan.tp2_price:
                    log.info("TP2 hit %s @ $%.2f — sell %d @ $%.2f",
                             plan.symbol, price, remaining, plan.tp2_price)
                    o = self._limit_sell(plan.symbol, remaining, plan.tp2_price)
                    if o:
                        self.broker.wait_for_fill(o.id, timeout=60)
                    return "target_reached"

                time.sleep(poll_secs)

            # Fixed EOD cutoff reached — cancel resting orders, flatten
            log.info("EOD cutoff (%s ET) — flattening %s", CONFIG.eod_close, plan.symbol)
            if tp1_order is not None and not tp1_done:
                self.broker.cancel_order(tp1_order)
            last = self._current_price(plan.symbol, market) or plan.entry
            self._aggressive_exit(plan.symbol, remaining, last)
            return "eod_close"
        finally:
            if self.stream:
                self.stream.stop()
