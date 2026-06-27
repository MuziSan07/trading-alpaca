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
                outcome = self.executor.manage(plan, self.market, filled)
                log.info("Trade on %s finished: %s", plan.symbol, outcome)
            write_daily_report(self.broker)
            return  # one trade per day

        log.info("No candidate approved by AI + risk today.")
        write_daily_report(self.broker)
