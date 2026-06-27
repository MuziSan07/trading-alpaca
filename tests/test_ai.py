"""
AI analyzer tests — no real Anthropic calls.
"""
from types import SimpleNamespace

from src.ai_analyzer import AIAnalyzer
from src.scanner import Candidate


def make_candidate():
    return Candidate(symbol="WXYZ", price=1.45, volume=8_500_000, move=0.25,
                     pct_change=0.20, popped_before=True, max_past_pop=0.55)


def test_disabled_ai_auto_approves():
    ai = AIAnalyzer()
    ai.enabled = False
    ai.client = None
    out = ai.evaluate(make_candidate())
    assert out["approve"] is True
    assert "disabled" in out["reason"].lower()


def _fake_client(text):
    msg = SimpleNamespace(content=[SimpleNamespace(text=text)])
    return SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: msg))


def test_parses_clean_json():
    ai = AIAnalyzer()
    ai.enabled = True
    ai.client = _fake_client('{"approve": true, "confidence": 80, "reason": "ok"}')
    out = ai.evaluate(make_candidate())
    assert out["approve"] is True
    assert out["confidence"] == 80


def test_strips_code_fences():
    ai = AIAnalyzer()
    ai.enabled = True
    ai.client = _fake_client('```json\n{"approve": false, "confidence": 10, "reason": "weak"}\n```')
    out = ai.evaluate(make_candidate())
    assert out["approve"] is False


def test_bad_response_defaults_to_no_trade():
    ai = AIAnalyzer()
    ai.enabled = True
    ai.client = _fake_client("not json at all")
    out = ai.evaluate(make_candidate())
    assert out["approve"] is False
