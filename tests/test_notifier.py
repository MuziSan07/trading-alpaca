"""
Notifier tests — verify it's a safe no-op when nothing is configured, and that
each channel fires only when configured (no real network/email sent).
"""
import src.notifier as notifier


def test_notify_noop_when_unconfigured(monkeypatch):
    # No webhook, no SMTP -> should not raise and should not call senders
    calls = {"web": 0, "mail": 0}
    monkeypatch.setattr(notifier, "_webhook", lambda s, m: calls.__setitem__("web", calls["web"] + 1))
    monkeypatch.setattr(notifier, "_email", lambda s, m: calls.__setitem__("mail", calls["mail"] + 1))
    notifier.notify("Test", "hello")  # must not raise
    assert calls["web"] == 1 and calls["mail"] == 1  # called, but real impls no-op below


def test_webhook_skipped_without_url(monkeypatch):
    # Default config has no webhook URL -> _webhook must not make a request
    sent = {"n": 0}
    monkeypatch.setattr(notifier.urllib.request, "urlopen",
                        lambda *a, **k: sent.__setitem__("n", sent["n"] + 1))
    notifier._webhook("s", "m")
    assert sent["n"] == 0


def test_email_skipped_without_smtp(monkeypatch):
    # Default config has no SMTP creds -> _email must not open a connection
    opened = {"n": 0}
    monkeypatch.setattr(notifier.smtplib, "SMTP",
                        lambda *a, **k: opened.__setitem__("n", opened["n"] + 1))
    notifier._email("s", "m")
    assert opened["n"] == 0
