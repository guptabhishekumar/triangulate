# Leg 2 — Nautilus Trader (event-driven)

A realistic, bar-by-bar simulation on a low-level `BacktestEngine`. The strategy
(`strategy.py`) receives one bar at a time, updates a hand-written **incremental**
MACD (`macd_indicator.py`, reusing `shared.indicators.ema_step`), detects a
crossover against the previous bar, and submits market orders that the simulated
venue fills on the **next** bar.

- **Indicator:** hand-written, O(1) per bar — not the built-in `MACD`.
- **Account:** `SIM` venue, `NETTING`, margin, $100,000, fixed 10,000-unit orders,
  **zero fees** (the default FX 0.2 bp fee is removed for parity with vectorbt).
- **Metrics:** computed from the strategy's per-bar equity snapshots (taken from
  Nautilus's own portfolio) via `shared/metrics.py`.

## Run

```bash
# Python 3.12 (Nautilus needs 3.12–3.14)
python -m venv .venv && .venv\Scripts\activate
pip install -r 02_nautilus/requirements.txt
python 02_nautilus/run.py
```

## Result (committed dataset)

| Total Return | Sharpe | Max Drawdown | Trades |
|---:|---:|---:|---:|
| −0.1340% | −0.1211 | −0.7249% | 484 |

## Two real gotchas solved here (documented in the root README & NOTES.md)

1. **`no market for EUR/USD.SIM`** — a market BUY needs an ask; a single BID bar
   series has none. Fixed by feeding a single **LAST**-price series.
2. **One-bar look-ahead** — feeding BID+ASK bars at identical timestamps let an
   order fill at the *signal bar's own open* (Sharpe shot up to ~6.8). Fixed with
   the single LAST series + **close-time** bar stamps, so fills land on the next
   bar's open. Sharpe returned to ≈ the other engines.
