# Response to Client Session Review (June 29–30)

Every item from your session summary, addressed cleanly in the repo (not ad-hoc
patches). All changes are covered by the test suite (**26 passing**).

## Your intended changes — applied properly
| Your change | Status | Where |
|---|---|---|
| Switch AI to local Ollama/Mistral | ✅ Done — `AI_PROVIDER=ollama` (default), `OLLAMA_MODEL=mistral`, `OLLAMA_HOST`. Anthropic still selectable. | `config.py`, `ai_analyzer.py` |
| Drop the `ANTHROPIC_API_KEY=local` hack | ✅ Done — "enabled" now depends on the **provider**, not a fake key. | `config.py.validate()`, `ai_analyzer.py` |
| SYSTEM prompt was too aggressive | ✅ Rewritten to a **balanced** prompt (selective, not rubber-stamp, not reject-all). Please still tune wording to taste. | `ai_analyzer.py` |
| Stop loss 3% → 6% | ✅ Done — default `STOP_PCT=0.06`. | `config.py`, `.env.example` |
| Max float → 2,000,000 (was 20M) | ✅ Done — default `MAX_FLOAT=2000000`. | `config.py`, `.env.example` |
| EOD forced close at 8:00 PM ET | ✅ Rewritten cleanly with `zoneinfo` (stdlib, no pytz) at a **fixed wall-clock** `EOD_CLOSE=20:00` ET — no more entry-relative timer. | `executor.py`, `config.py` |

## Bugs you hit — fixed
| Bug | Fix |
|---|---|
| `get_stock_snapshots` had no such attribute | ✅ Corrected to the SDK's singular `get_stock_snapshot` (verified against installed alpaca-py 0.43). |
| Recurring `IndentationError` in executor | ✅ Executor rewritten cleanly; EOD logic is one small, tested function. |
| WebSocket drops ("no close frame") crashing the bot | ✅ Stream now runs under a **supervised auto-reconnect** loop with capped backoff; added `is_stale()` health check. No more full-process restart just to reconnect. |
| Daily counter didn't reset properly | ✅ "Trading day" is now keyed to **US/Eastern** time, so it resets at ET midnight regardless of server timezone. |
| **No position recovery on restart** (biggest risk) | ✅ On startup the bot now **detects any open position and resumes managing it** (stop + take-profit + EOD). Wired into `run.py` (`--now`, scheduled startup, and a new `--recover`). |

## The unexplained −15.17% swing — likely root cause
**MSTU is a 2× leveraged MicroStrategy ETF** — it can move 15–20%+ in a day.
Your paper account was ~$99.5k, and the strategy allocates **90%** → ~$90k
notional in that leveraged name. The most probable cause of the ~$15k unrealized
loss: **the position was left unmanaged** — the `get_stock_snapshot` crash and/or
a WebSocket drop killed the monitoring loop, and with **no position recovery**,
the −6% stop never fired. The move then ran well past the stop before you closed
it manually.

The three fixes above (snapshot crash, WebSocket reconnect, **position
recovery**) directly close this hole: a restart now re-attaches a working stop.
Still: please pull the Alpaca **activity/order history** for that account to
confirm no stray duplicate order was placed — I can't see your account from here.

⚠️ Note on sizing: on a ~$100k paper account, 90% into a 2× leveraged ETF is a
very large, volatile position. Consider a smaller `CASH_ALLOCATION` and/or
excluding leveraged ETFs from the universe before live money.

## Extra safety I added
- `--recover` flag to manually re-protect an open position.
- `autorun.sh` rewritten as a clean supervised restarter (backoff, clean-exit aware).
- Fail-SAFE AI: if the model is unreachable, the bot **does not trade** (previously it auto-approved).

## Recommended before unattended paper again
1. `pip install -r requirements.txt` (adds `ollama`, `tzdata`).
2. `ollama pull mistral` and confirm `ollama serve` is running.
3. `python run.py --check`, then `python run.py --recover` to clear/monitor any leftover position.
4. Review the SYSTEM prompt wording in `ai_analyzer.py`.
5. Reconsider `CASH_ALLOCATION` and whether to exclude leveraged ETFs (MSTU, etc.).
