"""
Claude AI analysis agent.

Role is BOUNDED on purpose (client asked: "I don't want my AI going rogue"):
  - The AI only SCORES and gives a final yes/no + reasoning on the top candidate.
  - It CANNOT place orders or change risk rules. All hard limits (price, sizing,
    stop, exits, one-per-day) are enforced later in deterministic code.
If the AI is unavailable, the bot falls back to the rule-based highest-volume pick.
"""
from __future__ import annotations

import json

from anthropic import Anthropic

from .config import CONFIG
from .logger import get_logger
from .scanner import Candidate

log = get_logger("ai_analyzer")

SYSTEM = """You are a disciplined momentum-trading analyst for penny stocks.
You are given ONE pre-filtered candidate that already passed strict numeric
filters (price <= $5, volume >= 1M, up >= $0.20, rising price & volume,
popped >= $0.50 historically). Judge ONLY whether momentum looks genuine and
sustainable for a small intraday gain. Be conservative. You do NOT control
risk or sizing. Respond ONLY with compact JSON:
{"approve": true/false, "confidence": 0-100, "reason": "one sentence"}"""


class AIAnalyzer:
    def __init__(self) -> None:
        self.enabled = bool(CONFIG.anthropic_api_key)
        self.client = Anthropic(api_key=CONFIG.anthropic_api_key) if self.enabled else None

    def evaluate(self, c: Candidate) -> dict:
        if not self.enabled:
            log.warning("AI disabled (no key) — auto-approving rule-based pick")
            return {"approve": True, "confidence": 50, "reason": "AI disabled; rule-based"}

        prompt = (
            f"Candidate: {c.symbol}\n"
            f"Price: ${c.price:.2f}\n"
            f"Volume today: {c.volume:,.0f}\n"
            f"Move today: +${c.move:.2f} ({c.pct_change*100:.1f}%)\n"
            f"Largest past daily pop: ${c.max_past_pop:.2f}\n"
            f"Should we take this momentum trade?"
        )
        try:
            msg = self.client.messages.create(
                model=CONFIG.claude_model,
                max_tokens=200,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text.strip()
            # strip code fences if present
            text = text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            log.info(
                "AI on %s -> approve=%s conf=%s | %s",
                c.symbol, result.get("approve"), result.get("confidence"),
                result.get("reason"),
            )
            return result
        except Exception as e:  # noqa: BLE001
            log.error("AI evaluation failed (%s) — defaulting to NO trade", e)
            return {"approve": False, "confidence": 0, "reason": f"AI error: {e}"}
