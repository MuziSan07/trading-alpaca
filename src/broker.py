"""
Alpaca connection wrapper. All broker calls go through here so switching
between PAPER and LIVE is a single .env flag (ALPACA_PAPER).
"""
from __future__ import annotations

import time

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    LimitOrderRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    QueryOrderStatus,
    OrderStatus,
)

from .config import CONFIG
from .logger import get_logger

log = get_logger("broker")

_TERMINAL = {
    OrderStatus.CANCELED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
}


class Broker:
    def __init__(self) -> None:
        self.client = TradingClient(
            CONFIG.alpaca_api_key,
            CONFIG.alpaca_secret_key,
            paper=CONFIG.alpaca_paper,
        )
        mode = "PAPER" if CONFIG.alpaca_paper else "LIVE"
        log.info("Connected to Alpaca in %s mode", mode)

    # ---- Account ----
    def account(self):
        return self.client.get_account()

    def cash(self) -> float:
        return float(self.account().cash)

    def buying_power(self) -> float:
        return float(self.account().buying_power)

    def daytrade_count(self) -> int:
        return int(self.account().daytrade_count)

    def is_pattern_day_trader(self) -> bool:
        return bool(self.account().pattern_day_trader)

    # ---- Assets ----
    def is_tradable(self, symbol: str) -> bool:
        """Alpaca only trades listed stocks; OTC pennies are not tradable."""
        try:
            asset = self.client.get_asset(symbol)
            return bool(asset.tradable)
        except Exception as e:  # noqa: BLE001
            log.warning("Asset check failed for %s: %s", symbol, e)
            return False

    # ---- Positions / orders ----
    def positions(self):
        return self.client.get_all_positions()

    def open_orders(self):
        req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        return self.client.get_orders(req)

    def submit_limit_buy(self, symbol: str, qty: int, limit_price: float):
        order = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            limit_price=round(limit_price, 2),
            extended_hours=True,  # required for premarket
        )
        log.info("Submitting BUY %s x%d @ %.2f", symbol, qty, limit_price)
        return self.client.submit_order(order)

    def submit_limit_sell(self, symbol: str, qty: int, limit_price: float):
        order = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
            limit_price=round(limit_price, 2),
            extended_hours=True,
        )
        log.info("Submitting SELL %s x%d @ %.2f", symbol, qty, limit_price)
        return self.client.submit_order(order)

    def get_order(self, order_id):
        return self.client.get_order_by_id(order_id)

    def cancel_order(self, order_id) -> None:
        try:
            self.client.cancel_order_by_id(order_id)
            log.info("Cancelled order %s", order_id)
        except Exception as e:  # noqa: BLE001
            log.info("Could not cancel order %s (%s)", order_id, e)

    def wait_for_fill(self, order_id, timeout: int = 120, poll: int = 3) -> float:
        """Wait for an order to fill. Returns actual filled qty (handles partials)."""
        waited = 0
        while waited < timeout:
            o = self.get_order(order_id)
            if o.status == OrderStatus.FILLED:
                return float(o.filled_qty or 0)
            if o.status in _TERMINAL:
                log.warning("Order %s ended %s with %s filled", order_id, o.status, o.filled_qty)
                return float(o.filled_qty or 0)
            time.sleep(poll)
            waited += poll
        o = self.get_order(order_id)
        log.warning("Fill timeout on %s — %s shares filled so far", order_id, o.filled_qty)
        return float(o.filled_qty or 0)

    def close_position(self, symbol: str):
        log.info("Closing position %s", symbol)
        return self.client.close_position(symbol)

    def kill_switch(self):
        """Emergency: cancel all orders and liquidate everything."""
        log.warning("KILL SWITCH activated — cancelling orders & closing positions")
        self.client.cancel_orders()
        self.client.close_all_positions(cancel_orders=True)
