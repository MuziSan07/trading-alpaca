"""
Entry point.

Usage:
  python run.py            -> schedule daily run at SCAN_START (7 AM ET)
  python run.py --now      -> run one trading cycle immediately (for testing)
  python run.py --check    -> verify config + Alpaca connection only
"""
import sys
import threading

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import CONFIG
from src.logger import get_logger
from src.orchestrator import Orchestrator

log = get_logger("run")


def check_only() -> None:
    problems = CONFIG.validate()
    if problems:
        for p in problems:
            log.error("CONFIG: %s", p)
    else:
        log.info("Config OK.")
    try:
        from src.broker import Broker
        b = Broker()
        acct = b.account()
        log.info(
            "Alpaca OK | status=%s | cash=$%s | equity=$%s | PDT=%s | daytrades=%s",
            acct.status, acct.cash, acct.equity,
            acct.pattern_day_trader, acct.daytrade_count,
        )
    except Exception as e:  # noqa: BLE001
        log.error("Alpaca connection FAILED: %s", e)


def main() -> None:
    args = sys.argv[1:]

    # Always validate config first
    for p in CONFIG.validate():
        log.warning("CONFIG: %s", p)

    if "--check" in args:
        check_only()
        return

    if "--recover" in args:
        log.info("Recovery check only…")
        if not Orchestrator().recover():
            log.info("No open position to recover.")
        return

    if "--now" in args:
        orch = Orchestrator()
        # Always protect an already-open position before starting anything new.
        if orch.recover():
            return
        log.info("Running one cycle immediately…")
        orch.run_once()
        return

    # Scheduled mode: run every weekday at SCAN_START (7 AM ET premarket)
    hour, minute = CONFIG.scan_start.split(":")
    scheduler = BlockingScheduler(timezone="America/New_York")
    scheduler.add_job(
        lambda: Orchestrator().run_once(),
        "cron",
        day_of_week="mon-fri",
        hour=int(hour),
        minute=int(minute),
    )
    # On startup, resume protecting any position left open by a prior crash.
    def _startup_recovery():
        try:
            Orchestrator().recover()
        except Exception as e:  # noqa: BLE001
            log.error("Startup recovery failed: %s", e)

    threading.Thread(target=_startup_recovery, daemon=True).start()

    log.info("Scheduled daily run at %s ET (Mon-Fri). Waiting…", CONFIG.scan_start)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down.")


if __name__ == "__main__":
    main()
