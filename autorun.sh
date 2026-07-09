#!/usr/bin/env bash
# Supervised runner — restarts the bot if it exits unexpectedly.
#
# This is a safety net, NOT a crash mask: the bot now (a) auto-reconnects its
# WebSocket and (b) recovers/re-protects any open position on startup, so a
# restart here re-attaches the stop/TP/EOD to a live position instead of leaving
# it unmanaged. Run:  ./autorun.sh   (or via a process manager / systemd)
set -u
cd "$(dirname "$0")"

BACKOFF=5
MAX_BACKOFF=60

while true; do
  echo "[autorun] $(date '+%F %T') starting bot"
  python run.py
  code=$?
  if [ "$code" -eq 0 ]; then
    echo "[autorun] bot exited cleanly (0) — stopping supervisor"
    break
  fi
  echo "[autorun] bot exited (code $code) — restarting in ${BACKOFF}s"
  sleep "$BACKOFF"
  BACKOFF=$(( BACKOFF * 2 ))
  [ "$BACKOFF" -gt "$MAX_BACKOFF" ] && BACKOFF=$MAX_BACKOFF
done
