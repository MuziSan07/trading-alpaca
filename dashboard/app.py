"""
Web dashboard (Flask + Chart.js).

Run:  python -m dashboard.app    then open http://localhost:5000

Features: live account status, equity curve, scanned candidates, open position,
trade history, in-browser config editing (writes .env), and controls
(run-now / kill-switch). Degrades gracefully with simulated data when no API
keys are set, so it always renders for a demo.
"""
from __future__ import annotations

import json
import math
import os
import random
import threading
from datetime import date, datetime, timedelta

from flask import (
    Flask, jsonify, request, render_template, redirect, url_for, session,
)

from src.config import CONFIG
from src import state

app = Flask(__name__)
app.secret_key = os.getenv("DASHBOARD_SECRET", "") or os.urandom(24)


# ---------------- session auth ----------------
def _auth_enabled() -> bool:
    return bool(CONFIG.dashboard_password)


@app.before_request
def gate():
    if not _auth_enabled():
        return None  # no password configured -> localhost-only, open
    if request.endpoint in ("login", "static"):
        return None
    if session.get("auth"):
        return None
    if request.path.startswith("/api"):
        return jsonify({"error": "unauthorized"}), 401
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (request.form.get("username") == CONFIG.dashboard_user
                and request.form.get("password") == CONFIG.dashboard_password):
            session["auth"] = True
            return redirect(url_for("index"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

STATE_DIR = "state"
EQUITY_FILE = os.path.join(STATE_DIR, "equity_history.json")
ENV_FILE = ".env"

# Strategy params that are safe to edit from the browser (NOT secrets)
EDITABLE = [
    "MAX_PRICE", "MIN_VOLUME", "MIN_PRICE_MOVE", "HISTORICAL_POP",
    "CASH_ALLOCATION", "TP1_PCT", "TP1_SIZE", "TP2_PCT", "TP2_SIZE",
    "STOP_PCT", "MAX_TRADES_PER_DAY", "MAX_FLOAT", "SCAN_START",
]


# ---------------- broker (graceful) ----------------
_broker = None
_broker_error = None


def get_broker():
    global _broker, _broker_error
    if _broker is not None:
        return _broker
    try:
        from src.broker import Broker
        _broker = Broker()
        return _broker
    except Exception as e:  # noqa: BLE001
        _broker_error = str(e)
        return None


# ---------------- simulated candidates (demo / no keys) ----------------
_DEMO = [
    ("ABCD", 3.10, 4_200_000, 2.85, 2.90, 0.62, 30_000_000),
    ("WXYZ", 1.45, 8_500_000, 1.20, 1.22, 0.55, 18_000_000),
    ("MNOP", 6.80, 9_000_000, 6.50, 6.55, 1.10, 25_000_000),
    ("QRST", 2.05, 600_000, 1.80, 1.82, 0.40, 12_000_000),
    ("LMNO", 4.10, 2_100_000, 4.05, 4.02, 0.30, 9_000_000),
    ("HUGE", 2.40, 5_000_000, 2.15, 2.18, 0.70, 400_000_000),
]


def simulate_candidates():
    out = []
    for sym, price, vol, prev_close, open_, pop, flt in _DEMO:
        move = price - prev_close
        reasons = []
        if price > CONFIG.max_price:
            reasons.append(f"price > ${CONFIG.max_price:.2f}")
        if vol < CONFIG.min_volume:
            reasons.append("volume < 1M")
        if move < CONFIG.min_price_move:
            reasons.append(f"move < +${CONFIG.min_price_move:.2f}")
        if price < open_:
            reasons.append("price not rising")
        if pop < CONFIG.historical_pop:
            reasons.append(f"past pop < ${CONFIG.historical_pop:.2f}")
        if flt > CONFIG.max_float:
            reasons.append("float too high")
        out.append({
            "symbol": sym, "price": price, "volume": vol, "move": round(move, 2),
            "pop": pop, "float": flt, "passed": len(reasons) == 0,
            "reason": "PASS" if not reasons else reasons[0],
        })
    out.sort(key=lambda c: (not c["passed"], -c["volume"]))
    return out


# ---------------- equity history ----------------
def record_equity(equity: float):
    os.makedirs(STATE_DIR, exist_ok=True)
    hist = []
    if os.path.exists(EQUITY_FILE):
        try:
            hist = json.load(open(EQUITY_FILE))
        except Exception:  # noqa: BLE001
            hist = []
    hist.append({"t": datetime.now().strftime("%H:%M:%S"), "equity": equity})
    hist = hist[-200:]
    json.dump(hist, open(EQUITY_FILE, "w"))
    return hist


def simulated_equity():
    base = 1000.0
    return [{"t": (datetime.now() - timedelta(minutes=9 - i)).strftime("%H:%M"),
             "equity": round(base + base * 0.01 * (i - 4) * (1 if i % 2 else 0.6), 2)}
            for i in range(10)]


# ---------------- .env editing ----------------
def read_env_params():
    params = {k: getattr(CONFIG, k.lower(), "") for k in EDITABLE}
    return params


def write_env_params(updates: dict):
    lines = {}
    if os.path.exists(ENV_FILE):
        for ln in open(ENV_FILE):
            if "=" in ln and not ln.strip().startswith("#"):
                k = ln.split("=", 1)[0].strip()
                lines[k] = ln.rstrip("\n")
    # seed from .env.example if no .env yet
    elif os.path.exists(".env.example"):
        for ln in open(".env.example"):
            if "=" in ln and not ln.strip().startswith("#"):
                k = ln.split("=", 1)[0].strip()
                lines[k] = ln.rstrip("\n")

    for k, v in updates.items():
        if k in EDITABLE:
            lines[k] = f"{k}={v}"

    with open(ENV_FILE, "w") as f:
        f.write("# Updated via dashboard\n")
        for v in lines.values():
            f.write(v + "\n")


# ---------------- routes ----------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    b = get_broker()
    if b is None:
        eq = simulated_equity()
        return jsonify({
            "connected": False, "mode": "PAPER (no keys)",
            "equity": 1000.0, "cash": 1000.0, "buying_power": 1000.0,
            "daytrades": 0, "pdt": False, "trades_today": state.trades_today(),
            "equity_history": eq, "note": _broker_error or "Add API keys in .env",
        })
    try:
        acct = b.account()
        equity = float(acct.equity)
        hist = record_equity(equity)
        return jsonify({
            "connected": True,
            "mode": "PAPER" if CONFIG.alpaca_paper else "LIVE",
            "equity": equity, "cash": float(acct.cash),
            "buying_power": float(acct.buying_power),
            "daytrades": int(acct.daytrade_count),
            "pdt": bool(acct.pattern_day_trader),
            "trades_today": state.trades_today(),
            "equity_history": hist,
        })
    except Exception as e:  # noqa: BLE001
        return jsonify({"connected": False, "error": str(e)})


@app.route("/api/candidates")
def api_candidates():
    b = get_broker()
    if b is None:
        return jsonify({"simulated": True, "candidates": simulate_candidates()})
    try:
        from src.market_data import MarketData
        from src.scanner import Scanner
        cands = Scanner(MarketData()).scan()
        out = [{"symbol": c.symbol, "price": c.price, "volume": c.volume,
                "move": round(c.move, 2), "pop": c.max_past_pop, "float": None,
                "passed": True, "reason": "PASS"} for c in cands]
        ai = None
        if cands:
            try:
                from src.ai_analyzer import AIAnalyzer
                v = AIAnalyzer().evaluate(cands[0])
                ai = {"symbol": cands[0].symbol, "approve": v.get("approve"),
                      "confidence": v.get("confidence"), "reason": v.get("reason")}
            except Exception:  # noqa: BLE001
                ai = None
        return jsonify({"simulated": False, "candidates": out, "ai": ai})
    except Exception as e:  # noqa: BLE001
        return jsonify({"simulated": True, "error": str(e),
                        "candidates": simulate_candidates()})


@app.route("/api/intraday")
def api_intraday():
    sym = request.args.get("symbol", "")
    b = get_broker()
    if b is not None and sym:
        try:
            from src.market_data import MarketData
            bars = MarketData().intraday_bars(sym)
            if bars:
                return jsonify({"simulated": False, "symbol": sym,
                                "labels": [bp.timestamp.strftime("%H:%M") for bp in bars],
                                "prices": [float(bp.close) for bp in bars]})
        except Exception:  # noqa: BLE001
            pass
    # synthetic random-walk intraday for demo
    price = 1.45
    labels, prices = [], []
    t = datetime.now() - timedelta(minutes=90)
    for i in range(90):
        price = max(0.5, price + random.uniform(-0.02, 0.025))
        labels.append((t + timedelta(minutes=i)).strftime("%H:%M"))
        prices.append(round(price, 2))
    return jsonify({"simulated": True, "symbol": sym or "DEMO",
                    "labels": labels, "prices": prices})


@app.route("/api/position")
def api_position():
    b = get_broker()
    if b is None:
        return jsonify({"connected": False, "positions": []})
    try:
        pos = b.positions()
        return jsonify({"connected": True, "positions": [
            {"symbol": p.symbol, "qty": p.qty,
             "avg": float(p.avg_entry_price), "price": float(p.current_price),
             "pl": float(p.unrealized_pl), "pl_pct": float(p.unrealized_plpc) * 100}
            for p in pos]})
    except Exception as e:  # noqa: BLE001
        return jsonify({"connected": False, "error": str(e), "positions": []})


@app.route("/api/history")
def api_history():
    items = []
    sf = os.path.join(STATE_DIR, "daily_state.json")
    if os.path.exists(sf):
        try:
            d = json.load(open(sf))
            for s in d.get("symbols", []):
                items.append({"date": d.get("date"), "symbol": s})
        except Exception:  # noqa: BLE001
            pass
    reports = []
    if os.path.isdir("logs"):
        reports = sorted([f for f in os.listdir("logs")
                          if f.startswith("daily_report_")], reverse=True)
    return jsonify({"trades": items, "reports": reports})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        updates = request.get_json(force=True) or {}
        write_env_params(updates)
        return jsonify({"ok": True, "msg": "Saved to .env. Restart bot to apply."})
    return jsonify(read_env_params())


@app.route("/api/run", methods=["POST"])
def api_run():
    b = get_broker()
    if b is None:
        return jsonify({"ok": False, "msg": "Not connected — add API keys first."})

    def _run():
        from src.orchestrator import Orchestrator
        Orchestrator().run_once()

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"ok": True, "msg": "Trading cycle started (see logs)."})


@app.route("/api/kill", methods=["POST"])
def api_kill():
    b = get_broker()
    if b is None:
        return jsonify({"ok": False, "msg": "Not connected."})
    try:
        b.kill_switch()
        return jsonify({"ok": True, "msg": "KILL SWITCH executed — all flat."})
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "msg": str(e)})


if __name__ == "__main__":
    host, port = CONFIG.dashboard_host, CONFIG.dashboard_port
    if not CONFIG.dashboard_password and host not in ("127.0.0.1", "localhost"):
        print("WARNING: no DASHBOARD_PASSWORD set — forcing localhost-only binding.")
        host = "127.0.0.1"
    auth_state = "password-protected" if CONFIG.dashboard_password else "localhost-only (no password)"
    print(f"Dashboard running at http://{host}:{port}  [{auth_state}]")
    app.run(host=host, port=port, debug=False)
