# How to Get Your API Keys (5 minutes)

You need **two** sets of keys. Both have free tiers. Follow these steps and
paste the results into your `.env` file. **Never share these keys with anyone.**

---

## 1. Alpaca paper-trading keys (free)

1. Go to **https://app.alpaca.markets** and sign up / log in.
2. In the top-left, make sure you are in **"Paper Trading"** mode (toggle).
3. On the right side, find the **"API Keys"** panel and click **"Generate"**
   (or "Regenerate").
4. Copy the two values shown:
   - **API Key ID** (looks like `PK….`)
   - **Secret Key** (long string — shown only once, copy it now!)

Paste into `.env`:
```
ALPACA_API_KEY=PK......your key id......
ALPACA_SECRET_KEY=......your secret......
ALPACA_PAPER=true
```

> Tip: Paper trading gives you fake money to test safely. Real (live) keys are
> generated the same way but in "Live Trading" mode — we only switch to those
> once you're happy with the testing.

---

## 2. Anthropic (Claude) API key (for the AI analysis)

1. Go to **https://console.anthropic.com** and log in.
2. Open **Settings → API Keys**.
3. Click **"Create Key"**, name it (e.g. "trading-bot"), and copy it
   (looks like `sk-ant-….`).

Paste into `.env`:
```
ANTHROPIC_API_KEY=sk-ant-......your key......
```

> Note: this is a separate paid API (pay-per-use, very cheap for this bot —
> a few cents per day). It is **not** the same as your Claude Pro subscription.

---

## 3. Finish

1. In the project folder, copy the template:
   ```
   cp .env.example .env
   ```
2. Open `.env` and paste your 3 keys as above.
3. Test the connection:
   ```
   python run.py --check
   ```
   You should see your account status, cash, and "Alpaca OK".

That's it — you're ready. Send me a message once `--check` works and I'll run
a full paper session.
