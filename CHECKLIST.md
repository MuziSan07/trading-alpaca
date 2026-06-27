# Penny-Stock Momentum Trading Bot — Complete Build Checklist

> Client: **jberman93** (GitHub: `jibcampingcreations-a11y`) · Budget: **$1,200** · Deadline: **before July 4** · 3 revisions
> Stack: **Python + alpaca-py + Claude + Docker + GitHub** · Paper-trade first, then live.

Legend: `[ ]` = to do · `[~]` = in progress · `[x]` = done

---

## 📊 PROGRESS (updated June 27 — MVP built)

| Phase | Status |
|---|---|
| 0 — Setup (structure, config, Docker, gitignore, requirements) | ✅ Done |
| 1 — Alpaca connection (wrapper, paper/live, account, kill switch) | ✅ Done |
| 2 — Market data (universe, snapshots, bars, IEX/SIP toggle) | ✅ Done |
| 3 — Scanner (all 6 filters + highest-volume selection) | ✅ Done |
| 4 — AI/Claude agent (pop check, verdict, anti-rogue guardrail) | ✅ Done |
| 5 — Risk management (90% sizing, 3% stop, 1/day, PDT guard) | ✅ Done |
| 6 — Execution (buy + scale-out exits + stop, premarket limits) | ✅ Done |
| 7 — Orchestration (7 AM scheduler, daily flow, state) | ✅ Done |
| 8 — Security (keys, kill switch, audit log, **security_check.py + SECURITY.md**) | ✅ Done |
| 9 — Logging + **daily report (reporter.py)** | ✅ Done |
| 10 — Testing (**13 tests pass: strategy + risk + scanner mocks**) | 🟡 live paper run pending keys |
| 11 — Docs (README, CALL_GUIDE, DECISIONS, SECURITY, SETUP_KEYS, demo.py) | ✅ Done |
| 12 — Open decisions | ✅ free defaults set (DECISIONS.md); confirm w/ client phase 2 |

**Extras done:** WebSocket streaming (`stream.py`), partial-fill handling,
free yfinance float/volume, GitHub repo pushed (MuziSan07/trading-alpaca).

**Demo:** run `python demo.py` for a no-keys dry-run of the full pipeline.
**Only remaining:** client's API keys → live paper session.

---

## PHASE 0 — Project Setup & Foundations

### 0.1 Repository & environment
- [ ] Create GitHub repo (private) and add collaborator `jibcampingcreations-a11y`
- [ ] Add `README.md` (overview, setup steps, how to run)
- [ ] Add `.gitignore` (ignore `.env`, `__pycache__`, logs, secrets, `venv/`)
- [ ] Add `LICENSE` / usage notice
- [ ] Python project structure (`src/`, `tests/`, `config/`, `logs/`)
- [ ] `requirements.txt` (alpaca-py, anthropic, websockets, pandas, python-dotenv, pydantic, apscheduler, pytest)
- [ ] Virtual environment instructions for Mac (Homebrew + venv)

### 0.2 Configuration system
- [ ] `.env.example` template (no real keys committed)
- [ ] Load config from environment variables (`python-dotenv`)
- [ ] **Paper / Live toggle** (single switch — defaults to PAPER for safety)
- [ ] Central `config.py` with all strategy parameters (editable in one place):
  - [ ] Max price ($5.00)
  - [ ] Min volume (1,000,000)
  - [ ] Min price move (+$0.20)
  - [ ] Historical pop threshold (+$0.50)
  - [ ] Cash allocation % (90%)
  - [ ] Profit target 1 (+5% → sell 75%)
  - [ ] Profit target 2 (+7% → sell 25%)
  - [ ] Stop loss (−3%)
  - [ ] Max trades per day (1, configurable for future)
  - [ ] Scan start time (7:00 AM premarket)
  - [ ] Low float threshold
- [ ] Validate config on startup (fail fast if values missing/invalid)

### 0.3 Docker
- [ ] `Dockerfile` (Python base image, install deps, run app)
- [ ] `docker-compose.yml` (env file mount, log volume, timezone set)
- [ ] Set container timezone to **US/Eastern** (market time)
- [ ] Document `docker build` + `docker run` commands for the client's Mac

---

## PHASE 1 — Alpaca Connection Layer

- [ ] Install & wire up **`alpaca-py`** (official SDK, NOT deprecated `alpaca-trade-api`)
- [ ] Connect with **paper trading keys** first
- [ ] Test connection: fetch account info, cash balance, buying power
- [ ] Fetch open positions and open orders
- [ ] Handle auth errors gracefully (clear message if keys wrong)
- [ ] Confirm tradable-asset check (Alpaca only trades **listed** stocks — flag untradable symbols)
- [ ] Wrapper module for all broker calls (so live/paper swap is one line)

---

## PHASE 2 — Market Data & WebSocket Streaming

- [ ] Connect to Alpaca **market data WebSocket** (live quotes/trades/bars)
- [ ] Subscribe to real-time price + volume updates
- [ ] Auto-reconnect on dropped connection
- [ ] Historical bars fetch (for the "popped $0.50+ in the past" analysis)
- [ ] **Data feed handling** — IEX (free, partial volume) vs SIP (paid, full volume)
  - [ ] Make feed configurable
  - [ ] Document volume-accuracy limitation to client
- [ ] Premarket data handling (extended hours bars)
- [ ] Volume-trend tracking (is volume *increasing*?)
- [ ] Price-trend tracking (is price *increasing*?)

---

## PHASE 3 — The Scanner

> Finds candidate stocks each scan cycle.

- [ ] Build symbol universe (low-priced listed stocks ≤ $5)
- [ ] **Filter 1:** price ≤ $5.00
- [ ] **Filter 2:** volume ≥ 1,000,000
- [ ] **Filter 3:** price move ≥ +$0.20
- [ ] **Filter 4:** volume is increasing
- [ ] **Filter 5:** price is increasing
- [ ] **Filter 6:** low float filter
- [ ] Produce ranked candidate list
- [ ] Scanner runs on schedule starting **7:00 AM ET (premarket)**
- [ ] Logging of every candidate and why it passed/failed
- [ ] Configurable scan interval (e.g. every N seconds/minutes)

---

## PHASE 4 — AI / Claude Analysis Agent

> Bounded role: analyze & rank. It does NOT have free authority to place arbitrary trades.

- [ ] Integrate Anthropic Claude API (latest model)
- [ ] **Historical pop analysis** — has the stock jumped ≥ $0.50 in the past?
- [ ] Momentum-quality confirmation on candidates
- [ ] **Selection rule:** among qualifiers, pick the **HIGHEST volume** stock
- [ ] Structured output (JSON: chosen symbol, reasoning, confidence)
- [ ] **Guardrail:** AI output validated against hard rules in code before any action
- [ ] AI cannot override price/sizing/stop/exit rules (deterministic code enforces them)
- [ ] Log every AI decision with reasoning (for review/compliance)
- [ ] Graceful fallback if AI API fails (skip trade, don't crash)

---

## PHASE 5 — Risk Management Layer

> Enforced in deterministic code — the safety core.

- [ ] **Position sizing:** allocate 90% of available cash, compute share quantity
- [ ] **Stop loss:** −3% from entry
- [ ] **One-trade-per-day** enforcement (state persisted across restarts)
- [ ] Configurable max-trades-per-day (future-proof for >1)
- [ ] **PDT guardrail** — block trades that would breach Pattern Day Trader rule (<$25k account = max 3 day-trades / 5 days)
- [ ] Check sufficient buying power before ordering
- [ ] Reject untradable / non-Alpaca symbols
- [ ] Hard caps that neither bugs nor the AI can exceed
- [ ] Daily reset of counters at market open

---

## PHASE 6 — Order Execution Engine

- [ ] Place **buy order** (90% cash) — limit order for premarket compatibility
- [ ] Attach **exit logic:**
  - [ ] Sell **75% at +5%** profit
  - [ ] Sell **25% at +7%** profit
  - [ ] **Stop loss at −3%** on the whole position
- [ ] Use bracket / OCO orders where supported; manage scale-out manually where not
- [ ] **Premarket constraint:** limit orders only (no market orders pre-open)
- [ ] Order status tracking (filled / partial / rejected / canceled)
- [ ] Handle partial fills correctly in scale-out math
- [ ] Cancel/replace stale orders
- [ ] Confirm position closed end-of-day logic (avoid unwanted overnight holds)

---

## PHASE 7 — Orchestration / Main Loop

- [ ] Scheduler (APScheduler / cron) to start at 7 AM ET
- [ ] Main daily flow: scan → AI analyze → risk check → execute → monitor → exit
- [ ] Monitor open position live (via WebSocket) until exit conditions hit
- [ ] Stop after one trade/day (per config)
- [ ] Clean shutdown at market close
- [ ] State persistence (so restart doesn't double-trade)

---

## PHASE 8 — Security & Safety

> Directly addresses client's fears: "don't want hacking" + "don't want AI going rogue."

- [ ] API keys in `.env` / environment only — **never** hardcoded or committed
- [ ] Secrets excluded via `.gitignore` (verify before every push)
- [ ] Paper mode is the default — explicit action required to go live
- [ ] Hard-coded risk caps (cannot be exceeded by AI or bug)
- [ ] **Flagging system** — flag abnormal behavior (unexpected order size, repeated failures)
- [ ] Audit log of every decision and trade (compliance trail)
- [ ] Input validation on all external data (no blind trust of API responses)
- [ ] Rate-limit handling / backoff
- [ ] "Kill switch" — manual stop that halts all trading immediately
- [ ] Security review / testing pass before delivery

---

## PHASE 9 — Logging, Monitoring & Reporting

- [ ] Structured logging (timestamped, leveled) to file + console
- [ ] Trade log (entry, exits, P&L per trade)
- [ ] Scanner log (candidates considered)
- [ ] AI decision log (reasoning trail)
- [ ] Error/alert log
- [ ] Daily summary report (trades, P&L, account balance)
- [ ] Optional: notification on trade execution (email/console)

---

## PHASE 10 — Testing

- [ ] Unit tests: scanner filters
- [ ] Unit tests: position sizing math (90% allocation)
- [ ] Unit tests: exit math (75%@5%, 25%@7%, 3% stop)
- [ ] Unit tests: one-trade-per-day & PDT guard
- [ ] Mock Alpaca API for tests (no real calls)
- [ ] **Full end-to-end paper-trading run** (multiple market days)
- [ ] Edge cases: partial fills, API outage, no candidates, illiquid stock
- [ ] Stop-loss slippage test (penny stocks move fast)
- [ ] Verify premarket limit-order behavior

---

## PHASE 11 — Documentation & Handover

- [ ] `README.md` — full setup from zero on a Mac
- [ ] Step-by-step: create Alpaca account + get paper keys
- [ ] How to configure `.env`
- [ ] How to run via Docker
- [ ] How to switch paper → live
- [ ] How to change strategy parameters (config file)
- [ ] Explanation of each strategy rule (client is new to AI/code)
- [ ] Known limitations document (OTC pennies not on Alpaca, data feed, PDT)
- [ ] Troubleshooting guide
- [ ] Video-call walkthrough of the whole system

---

## PHASE 12 — Open Decisions (confirm with client on June 27 call)

- [ ] **PDT rule** — how to handle 3-day-trades/week limit on sub-$25k account
- [ ] **Universe** — accept listed $1–$5 stocks (true OTC pennies not on Alpaca)?
- [ ] **Data feed** — free IEX (partial volume) vs paid SIP (~$99/mo)?
- [ ] **Low-float & historical-pop data source** — which API/provider?
- [ ] Any final strategy tweaks the client wants to add
- [ ] Live-trading go/no-go criteria after paper testing

---

## Client Prerequisites (their side)
- [x] Python installed
- [x] Homebrew installed
- [x] GitHub account created
- [ ] Docker installed
- [ ] Alpaca account created + paper API keys generated
- [ ] (If needed) Paid data feed subscription
- [ ] Anthropic API key (for Claude)
