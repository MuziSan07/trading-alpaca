"""
Executor tests using fakes (no Alpaca, no network). Verifies premarket-safe
exits, fill-aware TP handling, and stop behavior.
"""
from alpaca.trading.enums import OrderStatus

from src.executor import Executor
from src.risk_manager import TradePlan


class FakeOrder:
    _n = 0

    def __init__(self, status=OrderStatus.FILLED):
        FakeOrder._n += 1
        self.id = f"o{FakeOrder._n}"
        self.status = status
        self.filled_qty = 0


class FakeStream:
    def __init__(self, prices):
        self.prices = list(prices)
    def start(self, sym): pass
    def stop(self): pass
    def get(self, sym):
        return self.prices.pop(0) if len(self.prices) > 1 else self.prices[0]


class FakeBroker:
    def __init__(self):
        self.sells = []      # (qty, price)
        self.cancels = []
        self.tp1_filled = True

    def submit_limit_buy(self, s, q, p):
        return FakeOrder()
    def submit_limit_sell(self, s, q, p):
        self.sells.append((q, round(p, 2)))
        return FakeOrder()
    def wait_for_fill(self, oid, timeout=120, poll=3):
        return 100.0
    def get_order(self, oid):
        return FakeOrder(OrderStatus.FILLED if self.tp1_filled else OrderStatus.NEW)
    def cancel_order(self, oid):
        self.cancels.append(oid)
    def close_position(self, s):
        self.sells.append(("ALL", 0))


def make_plan():
    return TradePlan(symbol="WXYZ", qty=100, entry=2.00, stop_price=1.94,
                     tp1_price=2.10, tp1_qty=75, tp2_price=2.14, tp2_qty=25)


def test_stop_uses_limit_order_not_market():
    b = FakeBroker()
    ex = Executor(b, stream=FakeStream([1.90]))
    out = ex.manage(make_plan(), market=None, filled_qty=100, poll_secs=0)
    assert out == "stopped"
    # exited the full 100 via a LIMIT sell (premarket-safe), priced below market
    assert b.sells and b.sells[0][0] == 100
    assert b.sells[0][1] < 1.94


def test_scale_out_targets_hit_in_order():
    b = FakeBroker()
    ex = Executor(b, stream=FakeStream([2.11, 2.20, 2.20]))
    out = ex.manage(make_plan(), market=None, filled_qty=100, poll_secs=0)
    assert out == "target_reached"
    # 75 sold at TP1, then 25 sold at TP2
    assert (75, 2.10) in b.sells
    assert (25, 2.14) in b.sells


def test_partial_fill_sizes_exits_from_real_qty():
    b = FakeBroker()
    ex = Executor(b, stream=FakeStream([1.50]))
    # only 40 shares actually filled -> stop should exit 40, not 100
    ex.manage(make_plan(), market=None, filled_qty=40, poll_secs=0)
    assert b.sells[0][0] == 40
