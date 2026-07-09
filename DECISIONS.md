# Strategy Decisions — LOCKED (free / open-source defaults)

All 6 open decisions are **decided and implemented** using free / open-source
tools, so the project is fully self-sufficient. Each is a one-line `.env` change
if the client ever wants something different.

| # | Decision | **LOCKED choice** | How it's enforced | Cost |
|---|---|---|---|---|
| 1 | **PDT rule** | 1 trade/day + PDT guard → auto-caps at 3 day-trades / 5 days when equity < $25k | `risk_manager.can_trade_today()` | Free, regulation-safe |
| 2 | **Universe** | Listed stocks priced **$1.00–$5.00** ($1 floor avoids illiquid sub-penny/OTC) | `MIN_PRICE` + `MAX_PRICE` in scanner | Free |
| 3 | **AI provider** | **Ollama + Mistral (local, free)** — client's choice in live session; Claude still selectable via `AI_PROVIDER=anthropic` | `AI_PROVIDER=ollama` | Free (local) |
| 3b | **Volume / data feed** | **Free IEX** for execution prices + **yfinance** for accurate volume & float | `ALPACA_DATA_FEED=iex` + `fundamentals.py` | $0 (vs ~$99/mo SIP) |
| 4 | **Low-float ceiling** | **2,000,000 shares** (client's intended threshold, updated from 20M) | `MAX_FLOAT=2000000` | Free |
| 4b | **Stop loss** | **6%** (client override from 3%, live session) | `STOP_PCT=0.06` | — |
| 4c | **EOD force-close** | **20:00 America/New_York**, fixed wall-clock | `EOD_CLOSE=20:00` | — |
| 5 | **Strategy tweaks** | Client's stated rules as-is + the $1 floor as the only safety add | scanner filters | — |
| 6 | **Go-live criteria** | **≥ 10 paper-trading days, no critical errors, break-even-or-better** before flipping to live | Operational policy + paper default | Free |

## Free stack (final)
- **Execution + account:** Alpaca paper API (free)
- **Candidate universe:** Alpaca most-actives screener (free)
- **Accurate volume + float:** yfinance / Yahoo Finance (free, open-source)
- **AI analysis:** Claude (client's Anthropic key)
- **Dashboard / backtest / CI:** all free & local

## To change any of these later
Edit `.env` (e.g. `MAX_FLOAT`, `MIN_PRICE`, `ALPACA_DATA_FEED`) and restart —
no code changes needed. Nothing is hard-locked; these are just the sensible
free defaults chosen so the build is complete without waiting on anyone.
