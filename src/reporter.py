"""
End-of-cycle daily summary report. Writes a human-readable P&L snapshot to
logs/daily_report_<date>.txt and logs it (audit trail).
"""
from __future__ import annotations

import os
from datetime import date

from .broker import Broker
from .logger import get_logger
from . import state

log = get_logger("reporter")
REPORT_DIR = "logs"


def write_daily_report(broker: Broker) -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    today = date.today().isoformat()
    acct = broker.account()

    lines = [
        "=" * 50,
        f" DAILY REPORT — {today}",
        "=" * 50,
        f" Account status   : {acct.status}",
        f" Equity           : ${float(acct.equity):,.2f}",
        f" Cash             : ${float(acct.cash):,.2f}",
        f" Buying power      : ${float(acct.buying_power):,.2f}",
        f" Day-trade count   : {acct.daytrade_count}",
        f" Trades today      : {state.trades_today()}",
    ]

    positions = broker.positions()
    if positions:
        lines.append(" Open positions:")
        for p in positions:
            lines.append(
                f"   {p.symbol}: {p.qty} @ avg ${float(p.avg_entry_price):.2f} "
                f"| unrealized P&L ${float(p.unrealized_pl):,.2f}"
            )
    else:
        lines.append(" Open positions   : none (flat)")
    lines.append("=" * 50)

    report = "\n".join(lines)
    path = os.path.join(REPORT_DIR, f"daily_report_{today}.txt")
    with open(path, "w") as f:
        f.write(report + "\n")
    log.info("Daily report written to %s", path)
    for ln in lines:
        log.info(ln)
    return path
