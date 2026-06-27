"""
Risk-manager tests using a FAKE broker (no real Alpaca calls).
"""
from types import SimpleNamespace

import pytest

from src.risk_manager import RiskManager


class FakeBroker:
    def __init__(self, cash=1000.0, equity=1000.0, daytrades=0, tradable=True):
        self._cash = cash
        self._equity = equity
        self._daytrades = daytrades
        self._tradable = tradable

    def cash(self):
        return self._cash

    def account(self):
        return SimpleNamespace(equity=self._equity, daytrade_count=self._daytrades)

    def is_tradable(self, symbol):
        return self._tradable


def test_build_plan_sizing_and_levels():
    rm = RiskManager(FakeBroker(cash=1000.0))
    plan = rm.build_plan("WXYZ", 1.45)
    assert plan is not None
    assert plan.qty == 620            # 900 / 1.45
    assert plan.stop_price == 1.41    # -3%
    assert plan.tp1_price == 1.52     # +5%
    assert plan.tp2_price == 1.55     # +7%
    assert plan.tp1_qty + plan.tp2_qty == plan.qty
    assert plan.tp1_qty == 465        # 75%


def test_build_plan_rejects_untradable():
    rm = RiskManager(FakeBroker(tradable=False))
    assert rm.build_plan("OTCX", 2.00) is None


def test_build_plan_rejects_insufficient_cash():
    rm = RiskManager(FakeBroker(cash=1.0))
    assert rm.build_plan("WXYZ", 5.00) is None


def test_pdt_guard_blocks_fourth_daytrade(monkeypatch):
    import src.risk_manager as rmmod
    monkeypatch.setattr(rmmod.state, "trades_today", lambda: 0)
    rm = RiskManager(FakeBroker(equity=5000.0, daytrades=3))
    ok, reason = rm.can_trade_today()
    assert ok is False
    assert "PDT" in reason


def test_daily_limit_blocks_second_trade(monkeypatch):
    import src.risk_manager as rmmod
    monkeypatch.setattr(rmmod.state, "trades_today", lambda: 1)
    rm = RiskManager(FakeBroker(equity=5000.0, daytrades=0))
    ok, reason = rm.can_trade_today()
    assert ok is False
    assert "limit" in reason.lower()


def test_can_trade_when_clear(monkeypatch):
    import src.risk_manager as rmmod
    monkeypatch.setattr(rmmod.state, "trades_today", lambda: 0)
    rm = RiskManager(FakeBroker(equity=5000.0, daytrades=0))
    ok, _ = rm.can_trade_today()
    assert ok is True
