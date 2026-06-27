"""
Notifications — free & optional. Sends alerts on trades and errors via:
  - console/log (always on)
  - Slack/Discord webhook (set NOTIFY_WEBHOOK_URL)
  - email over SMTP (set SMTP_* + NOTIFY_EMAIL_TO; e.g. free Gmail app password)

Everything is best-effort and non-blocking: if a channel isn't configured or
fails, it logs a warning and the bot keeps trading.
"""
from __future__ import annotations

import json
import smtplib
import urllib.request
from email.mime.text import MIMEText

from .config import CONFIG
from .logger import get_logger

log = get_logger("notifier")


def notify(subject: str, message: str) -> None:
    log.info("NOTIFY | %s | %s", subject, message)
    _webhook(subject, message)
    _email(subject, message)


def _webhook(subject: str, message: str) -> None:
    url = CONFIG.notify_webhook_url
    if not url:
        return
    try:
        data = json.dumps({"text": f"*{subject}*\n{message}"}).encode()
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:  # noqa: BLE001
        log.warning("Webhook notify failed: %s", e)


def _email(subject: str, message: str) -> None:
    if not (CONFIG.smtp_host and CONFIG.smtp_user and CONFIG.smtp_pass
            and CONFIG.notify_email_to):
        return
    try:
        msg = MIMEText(message)
        msg["Subject"] = f"[TradingBot] {subject}"
        msg["From"] = CONFIG.smtp_user
        msg["To"] = CONFIG.notify_email_to
        with smtplib.SMTP(CONFIG.smtp_host, CONFIG.smtp_port, timeout=15) as s:
            s.starttls()
            s.login(CONFIG.smtp_user, CONFIG.smtp_pass)
            s.send_message(msg)
    except Exception as e:  # noqa: BLE001
        log.warning("Email notify failed: %s", e)
