"""
Central configuration. Every strategy parameter lives here and is loaded from
the .env file so the client can tweak the strategy WITHOUT touching code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _f(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _i(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class Config:
    # --- API credentials ---
    alpaca_api_key: str = os.getenv("ALPACA_API_KEY", "")
    alpaca_secret_key: str = os.getenv("ALPACA_SECRET_KEY", "")
    alpaca_paper: bool = os.getenv("ALPACA_PAPER", "true").lower() != "false"
    data_feed: str = os.getenv("ALPACA_DATA_FEED", "iex")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    # --- Strategy parameters ---
    max_price: float = _f("MAX_PRICE", 5.00)              # penny stocks <= $5
    min_volume: int = _i("MIN_VOLUME", 1_000_000)         # high volume filter
    min_price_move: float = _f("MIN_PRICE_MOVE", 0.20)    # +$0.20 move
    historical_pop: float = _f("HISTORICAL_POP", 0.50)    # popped >= $0.50 before
    cash_allocation: float = _f("CASH_ALLOCATION", 0.90)  # use 90% of cash

    tp1_pct: float = _f("TP1_PCT", 0.05)    # +5% -> sell 75%
    tp1_size: float = _f("TP1_SIZE", 0.75)
    tp2_pct: float = _f("TP2_PCT", 0.07)    # +7% -> sell remaining 25%
    tp2_size: float = _f("TP2_SIZE", 0.25)
    stop_pct: float = _f("STOP_PCT", 0.03)  # -3% stop loss

    max_trades_per_day: int = _i("MAX_TRADES_PER_DAY", 1)
    max_float: int = _i("MAX_FLOAT", 50_000_000)  # low-float ceiling
    scan_start: str = os.getenv("SCAN_START", "07:00")  # 7 AM ET premarket

    # --- Dashboard security ---
    dashboard_user: str = os.getenv("DASHBOARD_USER", "admin")
    dashboard_password: str = os.getenv("DASHBOARD_PASSWORD", "")
    dashboard_host: str = os.getenv("DASHBOARD_HOST", "127.0.0.1")  # localhost only
    dashboard_port: int = _i("DASHBOARD_PORT", 5000)

    def validate(self) -> list[str]:
        """Return a list of problems; empty list means config is OK."""
        problems = []
        if not self.alpaca_api_key or not self.alpaca_secret_key:
            problems.append("Missing ALPACA_API_KEY / ALPACA_SECRET_KEY in .env")
        if not self.anthropic_api_key:
            problems.append("Missing ANTHROPIC_API_KEY in .env (AI analysis disabled)")
        if not (0 < self.cash_allocation <= 1):
            problems.append("CASH_ALLOCATION must be between 0 and 1")
        if abs((self.tp1_size + self.tp2_size) - 1.0) > 0.001:
            problems.append("TP1_SIZE + TP2_SIZE must equal 1.0 (100% of position)")
        return problems


CONFIG = Config()
