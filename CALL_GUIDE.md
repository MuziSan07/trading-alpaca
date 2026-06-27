# Video Call Talking Points — jberman93 (June 27, 7 PM PKT)

Goal of the call: show real progress, build trust, and lock the 6 open decisions.

---

## 1. Open warmly (1 min)
- Thank him for his patience.
- "I've built a working MVP of your bot — I'll walk you through it live, then
  there are a few trading decisions only you can make."

## 2. Show the dry-run demo (3 min)  ⭐ the wow moment
Run this on screen — no keys needed:
```
python demo.py
```
Narrate as it prints:
- "It scanned the active board and **applied your exact filters** — ≤$5, 1M+
  volume, +$0.20 move, rising price & volume, $0.50 past pop."
- "It threw out the $6.80 stock, the low-volume one, the weak mover."
- "Then it **picked the highest-volume** survivor — your rule."
- "Claude gave a momentum verdict — but **it can't touch your risk rules**,
  that answers your 'AI going rogue' worry."
- "Risk manager sized it to **90% of $1,000**, set the **−3% stop**, and the
  **75% @ +5% / 25% @ +7%** exits — exactly your strategy."

## 3. Show the code is real (2 min)
- Open the folder: 17 files, organized modules.
- "Every parameter is in one `.env` file — you can tweak the strategy yourself
  without touching code."
- "5 automated tests pass, proving the math (360 shares on a $2.50 stock, etc.)."
- "Paper-trading by default — no real money until you decide."

## 4. The 6 decisions I need from him (5 min)
Be honest — these are real trading constraints, not bugs:

1. **PDT rule.** Under $25k, US accounts get **max 3 day-trades per 5 days**.
   Your one-per-day plan = 5/week, which breaches it. Options:
   (a) cap at 3/week, (b) use a cash account, (c) hold overnight. → *Which?*
2. **Universe.** Alpaca only trades **listed** stocks; true OTC pennies aren't
   available. OK to target listed $1–$5 stocks? → *Confirm.*
3. **Data feed.** Free feed shows partial volume — and your whole strategy is
   volume-based. Paid SIP feed is ~$99/mo for accurate volume. → *Free or paid?*
4. **Low-float data.** Alpaca has no float data; needs a 3rd-party source.
   → *Add it now or in revision?*
5. **Any final strategy tweaks** he mentioned wanting.
6. **Go-live criteria** — how many good paper days before real money?

## 5. Next steps to state clearly
- "Next I wire in **your** Alpaca paper keys and run a full live paper session."
- "I'll push everything to the GitHub repo and add you (`jibcampingcreations-a11y`)."
- Confirm remaining timeline (well before July 4).

---

## Quick reassurance lines (he's nervous about money/security)
- "Keys live in a local `.env` file, never in the code or GitHub."
- "There's a kill switch that liquidates everything instantly."
- "Hard limits are in code — neither a bug nor the AI can exceed them."
- "It's paper money until you personally flip the switch to live."

## Things NOT to overpromise
- Don't claim it'll be profitable — it's a tool that executes HIS strategy.
- Don't claim true penny (OTC) stocks — Alpaca can't trade them.
- Don't claim accurate volume on the free feed.
