"""
Backtester — replays the strategy on free historical daily data (yfinance).

This is a DAILY-GRANULARITY approximation: it uses each day's high/low to decide
whether the stop or take-profits would have triggered. It is for validating the
strategy's logic and rough edge — NOT a tick-accurate simulation. Intraday
ordering of stop-vs-target is resolved conservatively (stop checked first).

Run:
  python -m src.backtest                 # default watchlist, 6 months
  python -m src.backtest AAPL F SOFI     # custom symbols
  python -m src.backtest --period 1y SOFI
"""
from __future__ import annotations

import sys

from .config import CONFIG
from .fundamentals import is_low_float
from .logger import get_logger

log = get_logger("backtest")

DEFAULT_WATCHLIST = ["SOFI", "F", "PLUG", "NIO", "SNAP", "RIG", "MARA", "GOLD"]


def _history(symbol: str, period: str):
    import yfinance as yf
    df = yf.Ticker(symbol).history(period=period)
    return df if df is not None and not df.empty else None


def run(symbols: list[str], period: str = "6mo", starting_cash: float = 1000.0) -> dict:
    frames = {}
    for s in symbols:
        df = _history(s, period)
        if df is not None:
            frames[s] = df
            log.info("Loaded %d bars for %s", len(df), s)
    if not frames:
        log.error("No data loaded — check symbols / connection.")
        return {}

    # unified ordered date list
    dates = sorted({d for df in frames.values() for d in df.index})

    equity = starting_cash
    realized = 0.0
    trades = []
    pos = None  # dict: symbol, entry, qty, remaining, tp1_done, stop, tp1, tp2

    for i, day in enumerate(dates):
        # ---- manage open position ----
        if pos:
            df = frames[pos["symbol"]]
            if day in df.index:
                bar = df.loc[day]
                low, high = float(bar["Low"]), float(bar["High"])
                # stop first (conservative)
                if low <= pos["stop"]:
                    pnl = (pos["stop"] - pos["entry"]) * pos["remaining"]
                    realized += pnl
                    trades.append({"symbol": pos["symbol"], "exit": "stop", "pnl": round(pnl, 2)})
                    pos = None
                else:
                    if not pos["tp1_done"] and high >= pos["tp1"]:
                        qty = int(pos["qty"] * CONFIG.tp1_size)
                        pnl = (pos["tp1"] - pos["entry"]) * qty
                        realized += pnl
                        pos["remaining"] -= qty
                        pos["tp1_done"] = True
                        trades.append({"symbol": pos["symbol"], "exit": "tp1", "pnl": round(pnl, 2)})
                    if pos and pos["tp1_done"] and high >= pos["tp2"]:
                        pnl = (pos["tp2"] - pos["entry"]) * pos["remaining"]
                        realized += pnl
                        trades.append({"symbol": pos["symbol"], "exit": "tp2", "pnl": round(pnl, 2)})
                        pos = None
            if pos:
                continue  # still holding -> one trade at a time

        # ---- scan for a new entry (flat) ----
        if i == 0:
            continue
        prev_day = dates[i - 1]
        candidates = []
        for s, df in frames.items():
            if day not in df.index or prev_day not in df.index:
                continue
            bar, prev = df.loc[day], df.loc[prev_day]
            price = float(bar["Close"])
            vol = float(bar["Volume"])
            move = price - float(prev["Close"])
            if price > CONFIG.max_price:
                continue
            if vol < CONFIG.min_volume:
                continue
            if move < CONFIG.min_price_move:
                continue
            if price < float(bar["Open"]):
                continue
            if vol < float(prev["Volume"]):
                continue
            # historical pop within the loaded window up to this day
            past = df.loc[:day]
            if (past["High"] - past["Low"]).max() < CONFIG.historical_pop:
                continue
            if not is_low_float(s, CONFIG.max_float):
                continue
            candidates.append((s, price, vol))

        if not candidates:
            continue
        candidates.sort(key=lambda c: c[2], reverse=True)  # highest volume
        sym, entry, _ = candidates[0]
        qty = int((equity * CONFIG.cash_allocation) // entry)
        if qty < 1:
            continue
        pos = {
            "symbol": sym, "entry": entry, "qty": qty, "remaining": qty,
            "tp1_done": False,
            "stop": round(entry * (1 - CONFIG.stop_pct), 4),
            "tp1": round(entry * (1 + CONFIG.tp1_pct), 4),
            "tp2": round(entry * (1 + CONFIG.tp2_pct), 4),
        }

    final_equity = starting_cash + realized
    wins = [t for t in trades if t["pnl"] > 0]
    summary = {
        "trades": len([t for t in trades if t["exit"] in ("stop", "tp2")]),
        "legs": len(trades),
        "wins": len(wins),
        "win_rate": round(100 * len(wins) / len(trades), 1) if trades else 0.0,
        "net_pnl": round(realized, 2),
        "return_pct": round(100 * realized / starting_cash, 2),
        "final_equity": round(final_equity, 2),
    }
    return {"summary": summary, "trades": trades}


def main():
    args = sys.argv[1:]
    period = "6mo"
    if "--period" in args:
        idx = args.index("--period")
        period = args[idx + 1]
        args = args[:idx] + args[idx + 2:]
    symbols = args or DEFAULT_WATCHLIST

    print(f"Backtesting {symbols} over {period}…\n")
    result = run(symbols, period=period)
    if not result:
        return
    s = result["summary"]
    print("=" * 50)
    print(" BACKTEST RESULT (daily-granularity approximation)")
    print("=" * 50)
    print(f" Completed trades : {s['trades']}")
    print(f" Exit legs        : {s['legs']}")
    print(f" Winning legs     : {s['wins']}  ({s['win_rate']}%)")
    print(f" Net P&L          : ${s['net_pnl']}")
    print(f" Return           : {s['return_pct']}%")
    print(f" Final equity     : ${s['final_equity']} (from $1000)")
    print("=" * 50)


if __name__ == "__main__":
    main()
