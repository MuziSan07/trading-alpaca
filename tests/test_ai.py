"""
AI analyzer tests — no real Anthropic/Ollama calls. Covers both providers and
the fail-SAFE behavior (disabled AI must NOT approve a blind trade).
"""
from types import SimpleNamespace

from src.ai_analyzer import AIAnalyzer
from src.scanner import Candidate


def make_candidate():
    return Candidate(symbol="WXYZ", price=1.45, volume=8_500_000, move=0.25,
                     pct_change=0.20, popped_before=True, max_past_pop=0.55)


def test_disabled_ai_rejects_fail_safe():
    ai = AIAnalyzer()
    ai.enabled = False
    ai.client = None
    out = ai.evaluate(make_candidate())
    assert out["approve"] is False  # fail safe: no blind trades


def _anthropic_client(text):
    msg = SimpleNamespace(content=[SimpleNamespace(text=text)])
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: msg))


def _ollama_client(text):
    return SimpleNamespace(chat=lambda **kw: {"message": {"content": text}})


def test_anthropic_parses_json():
    ai = AIAnalyzer()
    ai.enabled = True
    ai.provider = "anthropic"
    ai.client = _anthropic_client('{"approve": true, "confidence": 80, "reason": "ok"}')
    out = ai.evaluate(make_candidate())
    assert out["approve"] is True and out["confidence"] == 80


def test_ollama_parses_json_with_fences():
    ai = AIAnalyzer()
    ai.enabled = True
    ai.provider = "ollama"
    ai.client = _ollama_client('```json\n{"approve": false, "confidence": 20, "reason": "weak"}\n```')
    out = ai.evaluate(make_candidate())
    assert out["approve"] is False


def test_bad_response_defaults_to_no_trade():
    ai = AIAnalyzer()
    ai.enabled = True
    ai.provider = "ollama"
    ai.client = _ollama_client("not json at all")
    out = ai.evaluate(make_candidate())
    assert out["approve"] is False
