"""
Scanner tests using a FAKE market data source (no Alpaca, no yfinance/network).
"""
from types import SimpleNamespace

from src.scanner import Scanner


def bar(close, volume, open_, high=None, low=None):
    return SimpleNamespace(
        close=close, volume=volume, open=open_,
        high=high if high is not None else close,
        low=low if low is not None else close,
    )


def snap(close, volume, open_, prev_close, prev_volume):
    return SimpleNamespace(
        daily_bar=bar(close, volume, open_),
        previous_daily_bar=bar(prev_close, prev_volume, prev_close),
        latest_trade=SimpleNamespace(price=close),
    )


class FakeMarket:
    """Two stocks: WINR passes all filters; FAILR is too expensive."""
    def most_active_symbols(self, top=100):
        return ["WINR", "FAILR"]

    def snapshots(self, symbols):
        return {
            "WINR": snap(1.45, 8_500_000, 1.22, 1.20, 6_100_000),
            "FAILR": snap(6.80, 9_000_000, 6.55, 6.50, 7_000_000),
        }

    def daily_bars(self, symbol, days=30):
        # WINR has a past $0.60 pop; FAILR irrelevant (already filtered on price)
        return [bar(close=1.5, volume=1, open_=1.0, high=1.6, low=1.0)]


def test_scanner_passes_only_valid_and_picks_highest_volume(monkeypatch):
    # low-float filter -> always true (avoid network)
    monkeypatch.setattr("src.scanner.is_low_float", lambda sym, mx: True)

    scanner = Scanner(FakeMarket())
    results = scanner.scan()

    symbols = [c.symbol for c in results]
    assert "WINR" in symbols          # passed all filters
    assert "FAILR" not in symbols     # rejected: price > $5
    assert results[0].symbol == "WINR"  # highest-volume selection


def test_low_float_filter_excludes_high_float(monkeypatch):
    # Reject everything on float -> no candidates
    monkeypatch.setattr("src.scanner.is_low_float", lambda sym, mx: False)
    scanner = Scanner(FakeMarket())
    assert scanner.scan() == []
