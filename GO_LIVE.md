# Go-Live Runbook — from "keys arrived" to running

Follow top to bottom. Everything before "Switch to LIVE" uses **paper money**.

---

## 1. Install & configure (once)
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Paste into `.env`:
- `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` (paper) — keep `ALPACA_PAPER=true`
- `ANTHROPIC_API_KEY`
- *(optional)* `NOTIFY_WEBHOOK_URL` and/or SMTP settings for alerts
- *(optional)* `DASHBOARD_PASSWORD` if exposing the dashboard

## 2. Verify the connection
```bash
python run.py --check
```
✅ Expect: account status, cash, "Alpaca OK". ❌ If it errors, re-check the keys.

## 3. Smoke-test the pipeline
```bash
python demo.py            # no-keys dry run of the logic
python run.py --now       # ONE real paper cycle (scan -> AI -> maybe trade)
```
Watch `logs/trading_bot.log`. Confirm: scanner runs, AI responds, and if a
candidate qualifies, a **paper** order is placed and exits are managed.

## 4. Verify the live integrations (first real run checklist)
- [ ] Scanner returns candidates from real data (field shapes OK)
- [ ] Claude returns valid JSON verdict
- [ ] Order fills; `wait_for_fill` reports real qty
- [ ] WebSocket stream connects (price updates in logs)
- [ ] Stop / TP1 / TP2 fire as limit orders (premarket-safe)
- [ ] Daily report written to `logs/`
- [ ] Notifications arrive (if configured)

## 5. Run the dashboard
```bash
python -m dashboard.app   # http://127.0.0.1:5000
```
Check status, candidates, position, equity & intraday charts, config, controls.

## 6. Paper for real
```bash
python run.py             # scheduled daily at 7 AM ET (Mon–Fri)
```
Let it run on paper for **≥ 10 trading days**. Review daily reports.
Go-live bar: **no critical errors + break-even-or-better**.

## 7. Switch to LIVE (only after client approval)
1. Generate **live** keys in Alpaca (Live Trading mode).
2. In `.env`: set live keys and `ALPACA_PAPER=false`.
3. `python run.py --check` again, then start small.
4. Keep the kill switch handy: dashboard ⛔ button or `Broker.kill_switch()`.

---

## Quick troubleshooting
| Symptom | Likely cause / fix |
|---|---|
| `--check` auth error | Wrong/expired keys, or live keys used in paper mode |
| No candidates ever | Market closed, or filters too tight for the day (normal) |
| AI always rejects | Check `ANTHROPIC_API_KEY` and model name |
| Orders rejected premarket | Confirm extended-hours limit orders (already handled) |
| yfinance slow/blocked | Cache warms after first run; reduce universe if needed |
