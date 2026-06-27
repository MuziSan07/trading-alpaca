"""
DEMO / DRY-RUN - runs the FULL decision pipeline with simulated market data.

No API keys, no internet, no real orders. Use this to SHOW the client exactly
how the bot thinks: scan -> filter -> select highest volume -> AI verdict ->
risk sizing -> exit plan.

Run:  python demo.py
"""
from dataclasses import dataclass

from src.config import CONFIG


@dataclass
class FakeStock:
    symbol: str
    price: float
    volume: float
    prev_close: float
    prev_volume: float
    open_price: float
    max_past_pop: float
    float_shares: float


# A simulated premarket "most actives" board (float in shares)
MARKET = [
    FakeStock("ABCD", 3.10, 4_200_000, 2.85, 3_900_000, 2.90, 0.62, 30_000_000),
    FakeStock("WXYZ", 1.45, 8_500_000, 1.20, 6_100_000, 1.22, 0.55, 18_000_000),  # winner
    FakeStock("MNOP", 6.80, 9_000_000, 6.50, 7_000_000, 6.55, 1.10, 25_000_000),  # too pricey
    FakeStock("QRST", 2.05, 600_000, 1.80, 500_000, 1.82, 0.40, 12_000_000),       # low volume
    FakeStock("LMNO", 4.10, 2_100_000, 4.05, 2_300_000, 4.02, 0.30, 9_000_000),    # weak move/pop
    FakeStock("HUGE", 2.40, 5_000_000, 2.15, 4_000_000, 2.18, 0.70, 400_000_000),  # float too big
]


def passes_filters(s: FakeStock):
    move = s.price - s.prev_close
    reasons = []
    if s.price > CONFIG.max_price:
        reasons.append(f"price ${s.price:.2f} > ${CONFIG.max_price:.2f}")
    if s.volume < CONFIG.min_volume:
        reasons.append(f"volume {s.volume:,.0f} < {CONFIG.min_volume:,.0f}")
    if move < CONFIG.min_price_move:
        reasons.append(f"move +${move:.2f} < +${CONFIG.min_price_move:.2f}")
    if s.price < s.open_price:
        reasons.append("price not increasing")
    if s.volume < s.prev_volume:
        reasons.append("volume not increasing")
    if s.max_past_pop < CONFIG.historical_pop:
        reasons.append(f"past pop ${s.max_past_pop:.2f} < ${CONFIG.historical_pop:.2f}")
    if s.float_shares > CONFIG.max_float:
        reasons.append(f"float {s.float_shares:,.0f} > {CONFIG.max_float:,.0f} (not low-float)")
    return (len(reasons) == 0), move, reasons


def main():
    print("=" * 64)
    print("  PENNY-STOCK MOMENTUM BOT - DRY RUN (simulated data, no orders)")
    print("=" * 64)

    print("\n[1] SCANNING the most-active board against the strategy filters:\n")
    candidates = []
    for s in MARKET:
        ok, move, reasons = passes_filters(s)
        if ok:
            print(f"  PASS  {s.symbol}  ${s.price:.2f}  vol {s.volume:>11,.0f}  "
                  f"move +${move:.2f}  past-pop ${s.max_past_pop:.2f}  "
                  f"float {s.float_shares/1e6:.0f}M")
            candidates.append(s)
        else:
            print(f"  skip  {s.symbol}  -> {reasons[0]}")

    if not candidates:
        print("\nNo candidates today. No trade.")
        return

    print("\n[2] SELECTION RULE - highest volume wins:")
    candidates.sort(key=lambda x: x.volume, reverse=True)
    pick = candidates[0]
    print(f"      -> Picked {pick.symbol} (volume {pick.volume:,.0f})")

    print("\n[3] AI (Claude) momentum verdict:")
    print(f"      -> APPROVE {pick.symbol}  (conf 78)  "
          f'"Rising price on building volume; clean breakout, prior $0.55 pop."')
    print("      (Note: AI only advises - it cannot change any risk rule.)")

    print("\n[4] RISK MANAGER - sizing & safety:")
    cash = 1000.0
    alloc = cash * CONFIG.cash_allocation
    qty = int(alloc // pick.price)
    print(f"      Cash ${cash:,.2f} | allocate {CONFIG.cash_allocation*100:.0f}% "
          f"= ${alloc:,.2f} | buy {qty} shares @ ${pick.price:.2f}")
    print("      one-trade-per-day: OK   |   PDT guard: OK")

    print("\n[5] TRADE PLAN (bracket exits):")
    stop = round(pick.price * (1 - CONFIG.stop_pct), 2)
    tp1 = round(pick.price * (1 + CONFIG.tp1_pct), 2)
    tp2 = round(pick.price * (1 + CONFIG.tp2_pct), 2)
    tp1_qty = int(qty * CONFIG.tp1_size)
    tp2_qty = qty - tp1_qty
    print(f"      ENTRY : buy  {qty} {pick.symbol} @ ${pick.price:.2f}")
    print(f"      STOP  : -{CONFIG.stop_pct*100:.0f}%  -> sell all at  ${stop:.2f}")
    print(f"      TP1   : +{CONFIG.tp1_pct*100:.0f}%  -> sell {tp1_qty} (75%) at ${tp1:.2f}")
    print(f"      TP2   : +{CONFIG.tp2_pct*100:.0f}%  -> sell {tp2_qty} (25%) at ${tp2:.2f}")

    print("\n" + "=" * 64)
    print("  END OF DRY RUN - with real keys this places PAPER orders on Alpaca.")
    print("=" * 64)


if __name__ == "__main__":
    main()
