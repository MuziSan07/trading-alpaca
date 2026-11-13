# Session Review — Changes Applied

Every item from the session review, addressed cleanly in the repo (not ad-hoc
patches). All changes are covered by the test suite (**26 passing**).

## Intended changes — applied properly
| Change | Status | Where |
|---|---|---|
| Switch AI to local Ollama/Mistral | Done — `AI_PROVIDER=ollama` (default), `OLLAMA_MODEL=mistral`, `OLLAMA_HOST`. Anthropic still selectable. | `config.py`, `ai_analyzer.py` |
| Drop the `ANTHROPIC_API_KEY=local` hack | Done — "enabled" now depends on the **provider**, not a fake key. | `config.py.validate()`, `ai_analyzer.py` |
| SYSTEM prompt was too aggressive | Rewritten to a **balanced** prompt (selective, not rubber-stamp, not reject-all). Tune wording to taste. | `ai_analyzer.py` |
| Stop loss 3% -> 6% | Done — default `STOP_PCT=0.06`. | `config.py`, `.env.example` |
| Max float -> 2,000,000 (was 20M) | Done — default `MAX_FLOAT=2000000`. | `config.py`, `.env.example` |
| EOD forced close at 8:00 PM ET | Rewritten cleanly with `zoneinfo` (stdlib, no pytz) at a **fixed wall-clock** `EOD_CLOSE=20:00` ET — no more entry-relative timer. | `executor.py`, `config.py` |

## Bugs hit — fixed
| Bug | Fix |
|---|---|
| `get_stock_snapshots` had no such attribute | Corrected to the SDK's singular `get_stock_snapshot` (verified against installed alpaca-py 0.43). |
| Recurring `IndentationError` in executor | Executor rewritten cleanly; EOD logic is one small, tested function. |
| WebSocket drops ("no close frame") crashing the bot | Stream now runs under a **supervised auto-reconnect** loop with capped backoff; added `is_stale()` health check. No more full-process restart just to reconnect. |
| Daily counter didn't reset properly | Two-part fix: (1) "trading day" keyed to **US/Eastern** so it resets at ET midnight regardless of server tz; (2) **`RESET_ON_FLAT=true`** (default) — once the account is **flat**, the bot may evaluate new candidates again the same day. The real limiter is now "no open position" + the PDT guard; it also never stacks positions. Set `RESET_ON_FLAT=false` for a strict `MAX_TRADES_PER_DAY` cap. |
| **No position recovery on restart** (biggest risk) | On startup the bot now **detects any open position and resumes managing it** (stop + take-profit + EOD). Wired into `run.py` (`--now`, scheduled startup, and a new `--recover`). |

## Large unmanaged-position risk — root cause and fix
A big single-day swing is most likely when a large position is left **unmanaged**:
if the monitoring loop dies (for example the `get_stock_snapshot` crash and/or a
WebSocket drop) and there is **no position recovery**, the stop never fires and
the move can run well past it before anyone closes it manually. This risk is
amplified by **high-volatility instruments** (e.g. 2x leveraged ETFs, which can
move 15-20%+ in a day) combined with a large `CASH_ALLOCATION`.

The three fixes above (snapshot crash, WebSocket reconnect, **position
recovery**) directly close this hole: a restart now re-attaches a working stop.
As a safety check after any incident, pull the broker's **activity/order
history** to confirm no stray duplicate order was placed.

**Note on sizing:** a 90% allocation into a 2x leveraged ETF is a very large,
volatile position. Consider a smaller `CASH_ALLOCATION` and/or excluding
leveraged ETFs from the universe before using real money.

## Extra safety added
- `--recover` flag to manually re-protect an open position.
- `autorun.sh` rewritten as a clean supervised restarter (backoff, clean-exit aware).
- Fail-SAFE AI: if the model is unreachable, the bot **does not trade** (previously it auto-approved).

## Recommended before unattended paper again
1. `pip install -r requirements.txt` (adds `ollama`, `tzdata`).
2. `ollama pull mistral` and confirm `ollama serve` is running.
3. `python run.py --check`, then `python run.py --recover` to clear/monitor any leftover position.
4. Review the SYSTEM prompt wording in `ai_analyzer.py`.
5. Reconsider `CASH_ALLOCATION` and whether to exclude leveraged ETFs before live money.
