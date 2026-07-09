"""
Risk-manager tests using a FAKE broker (no real Alpaca calls).
"""
from types import SimpleNamespace

import pytest

from src.risk_manager import RiskManager


class FakeBroker:
    def __init__(self, cash=1000.0, equity=1000.0, daytrades=0, tradable=True, positions=None):
        self._cash = cash
        self._equity = equity
        self._daytrades = daytrades
        self._tradable = tradable
        self._positions = positions or []

    def cash(self):
        return self._cash

    def account(self):
        return SimpleNamespace(equity=self._equity, daytrade_count=self._daytrades)

    def positions(self):
        return self._positions

    def is_tradable(self, symbol):
        return self._tradable


def test_build_plan_sizing_and_levels():
    rm = RiskManager(FakeBroker(cash=1000.0))
    plan = rm.build_plan("WXYZ", 1.45)
    assert plan is not None
    assert plan.qty == 620            # 900 / 1.45
    assert plan.stop_price == 1.36    # -6%
    assert plan.tp1_price == 1.52     # +5%
    assert plan.tp2_price == 1.55     # +7%
    assert plan.tp1_qty + plan.tp2_qty == plan.qty
    assert plan.tp1_qty == 465        # 75%


def test_recovery_plan_rebuilds_protective_levels():
    rm = RiskManager(FakeBroker())
    plan = rm.recovery_plan("MSTU", entry=10.00, qty=90)
    assert plan.qty == 90
    assert plan.stop_price == 9.40    # -6%
    assert plan.tp1_price == 10.50    # +5%
    assert plan.tp2_price == 10.70    # +7%
    assert plan.tp1_qty + plan.tp2_qty == 90


def test_build_plan_rejects_untradable():
    rm = RiskManager(FakeBroker(tradable=False))
    assert rm.build_plan("OTCX", 2.00) is None


def test_build_plan_rejects_insufficient_cash():
    rm = RiskManager(FakeBroker(cash=1.0))
    assert rm.build_plan("WXYZ", 5.00) is None


def test_blocks_when_position_already_open():
    rm = RiskManager(FakeBroker(equity=5000.0, positions=["MSTU"]))
    ok, reason = rm.can_trade_today()
    assert ok is False
    assert "open" in reason.lower()


def test_pdt_guard_blocks_fourth_daytrade():
    rm = RiskManager(FakeBroker(equity=5000.0, daytrades=3, positions=[]))
    ok, reason = rm.can_trade_today()
    assert ok is False
    assert "PDT" in reason


def test_flat_account_allows_new_trade_even_after_one(monkeypatch):
    # reset_on_flat default True: closing the position frees a new evaluation
    import src.risk_manager as rmmod
    monkeypatch.setattr(rmmod.state, "trades_today", lambda: 1)
    rm = RiskManager(FakeBroker(equity=5000.0, daytrades=0, positions=[]))
    ok, _ = rm.can_trade_today()
    assert ok is True


def test_strict_daily_cap_when_reset_off(monkeypatch):
    import src.risk_manager as rmmod
    monkeypatch.setattr(rmmod.state, "trades_today", lambda: 1)
    object.__setattr__(rmmod.CONFIG, "reset_on_flat", False)  # frozen dataclass bypass
    try:
        rm = RiskManager(FakeBroker(equity=5000.0, daytrades=0, positions=[]))
        ok, reason = rm.can_trade_today()
        assert ok is False
        assert "limit" in reason.lower()
    finally:
        object.__setattr__(rmmod.CONFIG, "reset_on_flat", True)


def test_can_trade_when_clear_and_flat():
    rm = RiskManager(FakeBroker(equity=5000.0, daytrades=0, positions=[]))
    ok, _ = rm.can_trade_today()
    assert ok is True
