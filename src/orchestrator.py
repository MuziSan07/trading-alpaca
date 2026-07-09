"""
Orchestrator — the daily flow that ties every component together:

  scan -> AI analyze -> risk check -> execute entry -> manage exits

Scheduled to start at 7:00 AM ET (premarket) via run.py.
"""
from __future__ import annotations

from .ai_analyzer import AIAnalyzer
from .broker import Broker
from .executor import Executor
from .logger import get_logger
from .market_data import MarketData
from .notifier import notify
from .reporter import write_daily_report
from .risk_manager import RiskManager
from .scanner import Scanner
from .stream import PriceStream

log = get_logger("orchestrator")


class Orchestrator:
    def __init__(self) -> None:
        self.broker = Broker()
        self.market = MarketData()
        self.scanner = Scanner(self.market)
        self.ai = AIAnalyzer()
        self.risk = RiskManager(self.broker)
        self.stream = PriceStream()
        self.executor = Executor(self.broker, stream=self.stream)

    def recover(self) -> bool:
        """On startup, resume protecting any position left open (e.g. after a
        crash or restart). Without this, an open position's stop/TP/EOD would go
        unmanaged until noticed manually — the single biggest live-trading risk."""
        try:
            positions = self.broker.positions()
        except Exception as e:  # noqa: BLE001
            log.error("Recovery: could not fetch positions: %s", e)
            return False
        if not positions:
            return False

        p = positions[0]  # one-trade-per-day strategy -> at most one position
        symbol = p.symbol
        qty = int(float(p.qty))
        entry = float(p.avg_entry_price)
        log.warning("RECOVERY: open %s x%d @ $%.2f found — resuming management",
                    symbol, qty, entry)
        notify("Position recovery",
               f"Resuming management of {symbol} x{qty} @ ${entry:.2f}")
        plan = self.risk.recovery_plan(symbol, entry, qty)
        outcome = self.executor.manage(plan, self.market, qty, recovered=True)
        log.info("Recovered %s finished: %s", symbol, outcome)
        notify("Recovered position closed", f"{symbol}: {outcome}")
        write_daily_report(self.broker)
        return True

    def run_once(self) -> None:
        log.info("=" * 60)
        log.info("Starting trading cycle | cash=$%.2f", self.broker.cash())

        # 1. Daily limit / PDT guard
        ok, reason = self.risk.can_trade_today()
        if not ok:
            log.info("Not trading: %s", reason)
            write_daily_report(self.broker)
            return

        # 2. Scan
        candidates = self.scanner.scan()
        if not candidates:
            log.info("No candidates passed the filters today.")
            write_daily_report(self.broker)
            return
        log.info("%d candidate(s); top by volume: %s", len(candidates), candidates[0].symbol)

        # 3. Walk candidates (highest volume first) until AI + risk approve one
        for cand in candidates:
            verdict = self.ai.evaluate(cand)
            if not verdict.get("approve"):
                log.info("AI rejected %s: %s", cand.symbol, verdict.get("reason"))
                continue

            plan = self.risk.build_plan(cand.symbol, cand.price)
            if plan is None:
                continue

            # 4. Execute + manage (sized from the ACTUAL filled qty)
            filled = self.executor.enter(plan)
            if filled > 0:
                notify("Trade entered",
                       f"{plan.symbol}: bought {int(filled)} @ ~${plan.entry:.2f} "
                       f"(stop ${plan.stop_price:.2f}, TP ${plan.tp1_price:.2f}/${plan.tp2_price:.2f})")
                outcome = self.executor.manage(plan, self.market, filled)
                log.info("Trade on %s finished: %s", plan.symbol, outcome)
                notify("Trade closed", f"{plan.symbol}: {outcome}")
            write_daily_report(self.broker)
            return  # one trade per day

        log.info("No candidate approved by AI + risk today.")
        write_daily_report(self.broker)
