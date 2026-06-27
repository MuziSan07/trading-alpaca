# Penny-Stock Momentum Trading Bot

An automated penny-stock momentum day-trading bot for **Alpaca**, with a **Claude**
AI analysis layer, scale-out profit-taking, and hard risk guardrails.
Built in Python. **Paper-trading by default** — no real money moves until you say so.

---

## What it does (the strategy)

Every weekday at **7:00 AM ET (premarket)** it:

1. **Scans** the most-active stocks and keeps only those that pass ALL filters:
   - Price **≤ $5.00**
   - Volume **≥ 1,000,000**
   - Up **≥ $0.20** today
   - **Volume increasing** and **price increasing**
   - Has **popped ≥ $0.50** on a past day
2. **Selects the highest-volume** candidate.
3. **Claude AI** judges whether the momentum is genuine (advisory — it cannot
   override risk rules).
4. **Risk manager** sizes the position to **90% of cash** and runs safety checks
   (one-trade-per-day, PDT guard, tradable-symbol check).
5. **Executes** the buy and manages exits:
   - Sell **75% at +5%**
   - Sell **25% at +7%**
   - **Stop loss at −3%**

---

## Setup (Mac)

```bash
# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your keys
cp .env.example .env
#   then edit .env and paste your Alpaca PAPER keys + Anthropic key
```

### Get your keys
- **Alpaca paper keys:** https://app.alpaca.markets → *Paper Trading* → *API Keys*
- **Anthropic (Claude) key:** https://console.anthropic.com

---

## Run

```bash
python run.py --check    # verify config + Alpaca connection
python run.py --now      # run ONE trading cycle right now (testing)
python run.py            # schedule the daily 7 AM ET run
```

### Web dashboard
```bash
python -m dashboard.app
#  then open http://localhost:5000
```
A full browser dashboard: live equity chart, account status, scanned candidates
(with volume chart), AI pick, open position + P&L, trade history, daily reports,
**in-browser strategy config editing** (saves to `.env`), and controls
(run-cycle-now, refresh, kill switch). Works in demo mode with simulated data
before keys are added.

### With Docker
```bash
docker compose up --build
```

### Run the tests
```bash
pytest -v
```

---

## Going live (later)

Everything runs in **paper mode** by default. When you've tested thoroughly:
1. Generate **live** API keys in Alpaca.
2. Put them in `.env` and set `ALPACA_PAPER=false`.

The kill switch (`Broker.kill_switch()`) cancels all orders and liquidates
positions instantly if you ever need it.

---

## Tweaking the strategy

All parameters live in `.env` (no code changes needed): price cap, volume
threshold, move size, allocation %, profit targets, stop %, trades per day,
scan time. See `.env.example` for the full list.

---

## ⚠️ Important real-world notes

- **Alpaca trades only listed stocks.** True OTC sub-$1 pennies are NOT available;
  the universe is realistically low-priced *listed* stocks ($1–$5).
- **Accurate volume is FREE** via yfinance (Yahoo Finance) — no paid SIP feed
  needed. Alpaca's IEX feed is used only for execution prices. (Paid SIP remains
  an optional one-line upgrade: `ALPACA_DATA_FEED=sip`.)
- **Low-float filter is LIVE and FREE** via yfinance `floatShares`
  (ceiling = `MAX_FLOAT`, default 50M).
- **PDT rule:** accounts under $25k are limited to 3 day-trades per 5 business
  days. The bot blocks trades that would breach this.
- **Premarket = limit orders only** (handled automatically).

See `DECISIONS.md` for the demo defaults chosen for all 6 open questions.

---

## Project structure

```
run.py                 # entry point (scheduler + --now / --check)
src/
  config.py            # all strategy parameters (from .env)
  broker.py            # Alpaca wrapper (paper/live switch + kill switch)
  market_data.py       # universe, snapshots, historical bars
  scanner.py           # the 6 filters + highest-volume selection
  ai_analyzer.py       # Claude momentum check (bounded role)
  risk_manager.py      # sizing, stop/TP levels, one-per-day, PDT guard
  executor.py          # entry + scale-out exit management
  orchestrator.py      # daily flow tying it together
  state.py             # persisted one-trade-per-day tracking
  logger.py            # audit logging
tests/test_strategy.py # unit tests for the strategy math
```
