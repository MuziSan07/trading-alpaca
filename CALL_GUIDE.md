# Demo Walkthrough — Talking Points

Goal of the walkthrough: show real progress, build trust, and lock the open
strategy decisions.

---

## 1. Open warmly (1 min)
- "I've built a working MVP of the bot — I'll walk through it live, then there
  are a few trading decisions only you can make."

## 2. Show the dry-run demo (3 min) — the key moment
Run this on screen — no keys needed:
```
python demo.py
```
Narrate as it prints:
- "It scanned the active board and **applied the exact filters** — <=$5, 1M+
  volume, +$0.20 move, rising price & volume, $0.50 past pop."
- "It threw out the $6.80 stock, the low-volume one, the weak mover."
- "Then it **picked the highest-volume** survivor — the rule."
- "The AI gave a momentum verdict — but **it can't touch the risk rules**,
  which answers the 'AI going rogue' concern."
- "Risk manager sized it to **90% of the demo $1,000**, set the stop, and the
  **75% @ +5% / 25% @ +7%** exits — exactly the strategy."

## 3. Show the code is real (2 min)
- Open the folder: organized modules, one per responsibility.
- "Every parameter is in one `.env` file — you can tweak the strategy yourself
  without touching code."
- "Automated tests pass, proving the math (e.g. 360 shares on a $2.50 stock)."
- "Paper-trading by default — no real money until you decide."

## 4. The open decisions to confirm (5 min)
These are real trading constraints, not bugs:

1. **PDT rule.** Under $25k, US accounts get **max 3 day-trades per 5 days**.
   A one-per-day plan = 5/week, which breaches it. Options:
   (a) cap at 3/week, (b) use a cash account, (c) hold overnight.
2. **Universe.** Alpaca only trades **listed** stocks; true OTC pennies aren't
   available. Confirm targeting listed $1-$5 stocks.
3. **Data feed.** The free feed shows partial volume — and the strategy is
   volume-based. The paid SIP feed is ~$99/mo for accurate volume. Free or paid?
4. **Low-float data.** Alpaca has no float data; it needs a 3rd-party source
   (handled free via yfinance). Keep as-is or revisit?
5. **Any final strategy tweaks.**
6. **Go-live criteria** — how many good paper days before real money?

## 5. Next steps to state clearly
- "Next I wire in the Alpaca paper keys and run a full live paper session."
- "I'll push everything to the GitHub repo and add you as a collaborator."
- Confirm the remaining timeline.

---

## Quick reassurance lines (common money/security concerns)
- "Keys live in a local `.env` file, never in the code or on GitHub."
- "There's a kill switch that liquidates everything instantly."
- "Hard limits are in code — neither a bug nor the AI can exceed them."
- "It's paper money until you personally flip the switch to live."

## Things NOT to overpromise
- Don't claim it will be profitable — it's a tool that executes the strategy.
- Don't claim true penny (OTC) stocks — Alpaca can't trade them.
- Don't claim accurate volume on the free feed.
