"""
Reporter test — no Alpaca. Verifies a daily report file is written.
"""
import os
from types import SimpleNamespace

from src.reporter import write_daily_report


class FakeBroker:
    def account(self):
        return SimpleNamespace(status="ACTIVE", equity="1050.00", cash="150.00",
                               buying_power="150.00", daytrade_count=1,
                               pattern_day_trader=False)
    def positions(self):
        return [SimpleNamespace(symbol="WXYZ", qty="100",
                                avg_entry_price="1.45", unrealized_pl="5.00")]


def test_daily_report_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = write_daily_report(FakeBroker())
    assert os.path.exists(path)
    content = open(path).read()
    assert "DAILY REPORT" in content
    assert "1,050.00" in content
    assert "WXYZ" in content
