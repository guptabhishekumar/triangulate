# Leg 1 — vectorbt (vectorised)

Computes the whole MACD over NumPy arrays at once, turns it into boolean
entry/exit arrays, and runs `vbt.Portfolio.from_signals`.

- **Indicator:** hand-written (`shared/indicators.py`) — no `vbt.MACD`, no TA-Lib.
- **Execution:** signal on a closed bar → shift signals one bar and fill at the
  **next bar's open** (`price=open`), so there is no look-ahead.
- **Metrics:** recomputed from `pf.value()` via `shared/metrics.py` (vectorbt's own
  `pf.stats()` is also printed, for transparency).

## Run

```bash
# Python 3.12
python -m venv .venv && .venv\Scripts\activate     # (Windows)
pip install -r 01_vectorbt/requirements.txt
python 01_vectorbt/run.py
```

## Result (committed dataset)

| Total Return | Sharpe | Max Drawdown | Trades |
|---:|---:|---:|---:|
| −0.0536% | −0.0469 | −0.6565% | 484 |

This matches the glass-box reference engine (`shared/reference_backtest.py`)
**exactly**, confirming vectorbt is configured without look-ahead.
