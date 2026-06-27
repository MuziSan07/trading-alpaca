# Strategy Decisions — Demo Defaults (confirm with client in Phase 2)

These are the 6 open trading decisions. For the **demo**, I picked sensible
defaults using **free / open-source** tools so the bot works end-to-end today.
All are easily changed later via `.env` once the client confirms.

| # | Decision | Demo default (chosen now) | Why / cost | Confirm with client? |
|---|---|---|---|---|
| 1 | **PDT rule** (sub-$25k = max 3 day-trades / 5 days) | Keep 1 trade/day + PDT guard that blocks a breaching 4th day-trade | Safe, free, respects regulation | Yes — does he want cash account or 3/week cap? |
| 2 | **Universe** | Listed $1–$5 stocks via Alpaca's free most-actives screener | Alpaca can't trade OTC pennies anyway | Yes — confirm listed-only is OK |
| 3 | **Volume data feed** | **yfinance (free)** for accurate full-market volume; Alpaca IEX for execution prices | $0 vs ~$99/mo paid SIP | Yes — upgrade to SIP later if he wants |
| 4 | **Low-float data** | **yfinance floatShares (free)**, ceiling = 50M (`MAX_FLOAT`) | $0; real float data, no paid provider | Yes — confirm float ceiling |
| 5 | **Final strategy tweaks** | Use his stated rules as-is | — | Yes — ask if anything to add |
| 6 | **Go-live criteria** | Paper-trade only until he approves | Safety first | Yes — how many good paper days? |

## Free stack chosen
- **Execution + account:** Alpaca paper API (free)
- **Candidate universe:** Alpaca most-actives screener (free)
- **Accurate volume + float:** yfinance / Yahoo Finance (free, open-source)
- **AI analysis:** Claude (client already has Anthropic access)

All paid upgrades (SIP feed, premium float providers) remain optional and are a
one-line config change — nothing is locked in.
