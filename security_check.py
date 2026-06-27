"""
Automated security self-test. Run before every push / delivery:

    python security_check.py

Checks:
  1. No real secrets are hardcoded in source files
  2. .env is git-ignored (won't be pushed)
  3. Bot defaults to PAPER mode
  4. Risk hard-caps are sane (allocation <= 100%, stop > 0)
Exits non-zero if any check fails.
"""
from __future__ import annotations

import os
import re
import sys

FAIL = 0


def ok(msg: str) -> None:
    print(f"  [PASS] {msg}")


def bad(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  [FAIL] {msg}")


def check_no_hardcoded_secrets() -> None:
    # Alpaca keys look like PK........ / long base64; flag obvious literals
    patterns = [
        re.compile(r"PK[A-Z0-9]{16,}"),          # Alpaca key id
        re.compile(r"sk-ant-[A-Za-z0-9-]{20,}"),  # Anthropic key
    ]
    offenders = []
    for root, _, files in os.walk("."):
        if any(skip in root for skip in (".git", "venv", "__pycache__")):
            continue
        for fn in files:
            if not fn.endswith((".py", ".md", ".yml", ".yaml", ".txt")):
                continue
            if fn == "security_check.py":
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            for pat in patterns:
                if pat.search(content):
                    offenders.append(path)
    if offenders:
        bad(f"Possible hardcoded secret(s) in: {set(offenders)}")
    else:
        ok("No hardcoded API secrets found in source")


def check_env_ignored() -> None:
    if not os.path.exists(".gitignore"):
        bad(".gitignore missing")
        return
    with open(".gitignore") as f:
        content = f.read()
    if ".env" in content:
        ok(".env is git-ignored")
    else:
        bad(".env is NOT in .gitignore — secrets could be pushed!")
    if os.path.exists(".env"):
        print("  [warn] a real .env exists locally (fine, as long as it's ignored)")


def check_paper_default() -> None:
    with open(os.path.join("src", "config.py")) as f:
        content = f.read()
    if 'ALPACA_PAPER", "true"' in content:
        ok("Bot defaults to PAPER (safe) mode")
    else:
        bad("PAPER mode is not the default — risk of accidental live trading")


def check_risk_caps() -> None:
    from src.config import CONFIG
    if 0 < CONFIG.cash_allocation <= 1:
        ok(f"Cash allocation cap sane ({CONFIG.cash_allocation:.0%})")
    else:
        bad("Cash allocation out of bounds")
    if CONFIG.stop_pct > 0:
        ok(f"Stop loss configured ({CONFIG.stop_pct:.0%})")
    else:
        bad("Stop loss not configured")
    if CONFIG.max_trades_per_day >= 1:
        ok(f"Daily trade cap set ({CONFIG.max_trades_per_day})")
    else:
        bad("Daily trade cap invalid")


def main() -> None:
    print("Running security self-test…\n")
    check_no_hardcoded_secrets()
    check_env_ignored()
    check_paper_default()
    check_risk_caps()
    print()
    if FAIL:
        print(f"SECURITY CHECK FAILED — {FAIL} issue(s).")
        sys.exit(1)
    print("SECURITY CHECK PASSED — all clear.")


if __name__ == "__main__":
    main()
