# Security Review & Test Report

_Last run: automated via `python security_check.py` (passing)._

This document records the security posture of the trading bot and the tests
performed. It directly addresses the client's two concerns:
**"I don't want someone hacking my account"** and **"I don't want my AI going rogue."**

---

## Threat model

| Threat | Mitigation |
|---|---|
| API keys leaked via source / GitHub | Keys live only in local `.env`; `.env` is git-ignored; automated secret scan in `security_check.py` |
| Accidental live trading | Bot **defaults to PAPER**; going live requires an explicit `ALPACA_PAPER=false` |
| AI placing unintended / oversized trades | AI is **advisory only** — it returns approve/reject + reasoning; all order sizing & risk rules are enforced in deterministic code it cannot bypass |
| Runaway losses | Hard `-3%` stop, `90%` max allocation, **one trade/day**, PDT guard |
| Buying untradable / junk symbols | Tradable-symbol check before every order |
| Bad/malformed market data | Graceful handling; missing data does not force a trade |
| Need to stop everything fast | `Broker.kill_switch()` cancels all orders + liquidates all positions |
| No audit trail | Every scan, AI decision, and order is logged to `logs/` (rotating) + daily report |

---

## Automated checks (`security_check.py`)

Run before every push / delivery. Verifies:
1. **No hardcoded secrets** — scans all source for Alpaca (`PK…`) / Anthropic (`sk-ant-…`) key patterns.
2. **`.env` is git-ignored** — secrets cannot be pushed.
3. **Paper mode is the default** — no accidental live trading.
4. **Risk caps are sane** — allocation ≤ 100%, stop > 0, daily cap ≥ 1.

Current result: **ALL PASS.**

---

## Operational guidance for the client

- Generate **separate** paper and live keys; never share or commit them.
- Start in paper mode; only switch to live after a satisfactory paper period.
- On any concern, stop the bot (Ctrl-C) — or call the kill switch — and rotate
  your Alpaca keys from the dashboard.
- Use API keys scoped to the single account; do not reuse keys across apps.

---

## Known limitations (not security holes, but be aware)

- The free IEX feed shows partial volume; yfinance supplements it for free.
- Penny stocks can gap through a stop price; the stop is best-effort, not a guarantee.
