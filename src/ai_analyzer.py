"""
AI analysis agent — supports a local FREE model via Ollama (default) or Claude.

Role is BOUNDED on purpose ("I don't want my AI going rogue"):
  - The AI only SCORES and gives a final approve/reject + reasoning.
  - It CANNOT place orders or change risk rules. All hard limits (price, sizing,
    stop, exits, one-per-day) are enforced later in deterministic code.
If the AI provider is unavailable, the bot fails SAFE (no trade) rather than
trading blind.

Set AI_PROVIDER=ollama (local, free) or AI_PROVIDER=anthropic in .env.
"""
from __future__ import annotations

import json

from .config import CONFIG
from .logger import get_logger
from .scanner import Candidate

log = get_logger("ai_analyzer")

# Balanced prompt: neither rejects everything (original) nor rubber-stamps
# everything (the ad-hoc "aggressive" edit). It judges momentum quality on a
# candidate that already passed strict numeric filters.
SYSTEM = """You are a disciplined momentum-trading analyst for low-priced stocks.
You receive ONE candidate that ALREADY passed strict numeric filters (price
$1-$5, volume >= 1M, up >= $0.20 today, rising price & volume, low float,
popped >= $0.50 historically).

Your job: judge whether the momentum looks GENUINE and tradeable for a small
intraday gain, or whether it looks exhausted, erratic, or like a trap.
Approve solid continuation setups; reject weak, over-extended, or unclear ones.
Be selective but not paralysed — a clean qualifier should pass.

Respond with ONLY compact JSON, no prose:
{"approve": true/false, "confidence": 0-100, "reason": "one short sentence"}"""


def _user_prompt(c: Candidate) -> str:
    return (
        f"Candidate: {c.symbol}\n"
        f"Price: ${c.price:.2f}\n"
        f"Volume today: {c.volume:,.0f}\n"
        f"Move today: +${c.move:.2f} ({c.pct_change*100:.1f}%)\n"
        f"Largest past daily pop: ${c.max_past_pop:.2f}\n"
        f"Should we take this momentum trade?"
    )


def _parse(text: str) -> dict:
    text = text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text)


class AIAnalyzer:
    def __init__(self) -> None:
        self.provider = CONFIG.ai_provider
        self.client = None
        self.enabled = False
        try:
            if self.provider == "anthropic":
                if CONFIG.anthropic_api_key:
                    from anthropic import Anthropic
                    self.client = Anthropic(api_key=CONFIG.anthropic_api_key)
                    self.enabled = True
            else:  # ollama (default)
                import ollama
                self.client = ollama.Client(host=CONFIG.ollama_host)
                self.enabled = True
        except Exception as e:  # noqa: BLE001
            log.warning("AI provider '%s' unavailable: %s", self.provider, e)
            self.enabled = False

    def evaluate(self, c: Candidate) -> dict:
        if not self.enabled:
            # Fail SAFE: if the analyst is down, do not trade blind.
            log.warning("AI disabled (provider=%s) — rejecting to stay safe", self.provider)
            return {"approve": False, "confidence": 0,
                    "reason": f"AI provider {self.provider} unavailable"}
        try:
            if self.provider == "anthropic":
                msg = self.client.messages.create(
                    model=CONFIG.claude_model, max_tokens=200,
                    system=SYSTEM,
                    messages=[{"role": "user", "content": _user_prompt(c)}],
                )
                text = msg.content[0].text
            else:  # ollama
                resp = self.client.chat(
                    model=CONFIG.ollama_model,
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": _user_prompt(c)},
                    ],
                    options={"temperature": 0.2},
                )
                text = resp["message"]["content"]

            result = _parse(text)
            log.info("AI(%s) on %s -> approve=%s conf=%s | %s",
                     self.provider, c.symbol, result.get("approve"),
                     result.get("confidence"), result.get("reason"))
            return result
        except Exception as e:  # noqa: BLE001
            log.error("AI evaluation failed (%s) — defaulting to NO trade", e)
            return {"approve": False, "confidence": 0, "reason": f"AI error: {e}"}
