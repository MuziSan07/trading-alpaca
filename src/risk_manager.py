"""
Risk management — the deterministic safety core. Nothing (not even the AI)
can bypass these checks.

Enforces:
  - 90% cash allocation -> share quantity
  - one trade per day (configurable)
  - PDT guardrail (<$25k account = max 3 day-trades / 5 days)
  - tradable-symbol check
  - computes stop-loss and take-profit price levels
"""
from __future__ import annotations

from dataclasses import dataclass

from .broker import Broker
from .config import CONFIG
from .logger import get_logger
from . import state

log = get_logger("risk")


@dataclass
class TradePlan:
    symbol: str
    qty: int
    entry: float
    stop_price: float
    tp1_price: float
    tp1_qty: int
    tp2_price: float
    tp2_qty: int


class RiskManager:
    def __init__(self, broker: Broker) -> None:
        self.broker = broker

    def can_trade_today(self) -> tuple[bool, str]:
        # Never stack: only one position at a time.
        try:
            if self.broker.positions():
                return False, "A position is already open"
        except Exception as e:  # noqa: BLE001
            log.warning("Could not check open positions: %s", e)

        # PDT guardrail — the real limiter for a <$25k day-trading account.
        acct = self.broker.account()
        equity = float(acct.equity)
        if equity < 25_000 and int(acct.daytrade_count) >= 3:
            return False, "PDT limit: <$25k account already has 3 day-trades in 5 days"

        # Calendar cap: enforced only when NOT resetting on a flat account.
        # With reset_on_flat=True, closing the position (going flat) frees the
        # bot to evaluate new candidates again — bounded by the PDT guard above.
        if not CONFIG.reset_on_flat and state.trades_today() >= CONFIG.max_trades_per_day:
            return False, "Daily trade limit reached"
        return True, "ok"

    def build_plan(self, symbol: str, price: float) -> TradePlan | None:
        if not self.broker.is_tradable(symbol):
            log.warning("%s is not tradable on Alpaca (likely OTC) — skipping", symbol)
            return None

        cash = self.broker.cash()
        allocation = cash * CONFIG.cash_allocation
        qty = int(allocation // price)
        if qty < 1:
            log.warning("Not enough cash for even 1 share of %s @ $%.2f", symbol, price)
            return None

        stop_price = round(price * (1 - CONFIG.stop_pct), 2)
        tp1_price = round(price * (1 + CONFIG.tp1_pct), 2)
        tp2_price = round(price * (1 + CONFIG.tp2_pct), 2)
        tp1_qty = int(qty * CONFIG.tp1_size)
        tp2_qty = qty - tp1_qty  # remainder to avoid rounding leftovers

        plan = TradePlan(
            symbol=symbol, qty=qty, entry=price,
            stop_price=stop_price,
            tp1_price=tp1_price, tp1_qty=tp1_qty,
            tp2_price=tp2_price, tp2_qty=tp2_qty,
        )
        log.info(
            "PLAN %s: buy %d @ ~$%.2f | stop $%.2f | TP1 %d @ $%.2f | TP2 %d @ $%.2f",
            symbol, qty, price, stop_price, tp1_qty, tp1_price, tp2_qty, tp2_price,
        )
        return plan

    def recovery_plan(self, symbol: str, entry: float, qty: int) -> TradePlan:
        """Rebuild a protective plan for a position found already open (restart)."""
        tp1_qty = int(qty * CONFIG.tp1_size)
        return TradePlan(
            symbol=symbol, qty=qty, entry=entry,
            stop_price=round(entry * (1 - CONFIG.stop_pct), 2),
            tp1_price=round(entry * (1 + CONFIG.tp1_pct), 2),
            tp1_qty=tp1_qty,
            tp2_price=round(entry * (1 + CONFIG.tp2_pct), 2),
            tp2_qty=qty - tp1_qty,
        )
